"""Run schema diagnostics from `textgraphx/schema/ontology.json` and assert thresholds.

Intended for CI: the script exits with code 0 when all diagnostics are inside
their configured thresholds and non-zero otherwise. Each diagnostic should be a
mapping with keys: name, query, optional min, optional max.

Usage:
    python -m textgraphx.tools.schema_asserts [--config PATH] [--dry-run]

Examples:
    python -m textgraphx.tools.schema_asserts
    python -m textgraphx.tools.schema_asserts --config path/to/config.ini
    python -m textgraphx.tools.schema_asserts --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

from textgraphx.database.client import make_graph_from_config

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_ontology(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_diagnostic(graph, diag: Dict[str, Any]) -> Any:
    """Run a single diagnostic query and return the first row or value."""
    q = diag.get("query")
    if not q:
        raise ValueError(f"Diagnostic {diag.get('name')} has no 'query' field")
    rows = graph.run(q).data()
    if not rows:
        return None
    # If the row is a mapping with 'cnt' prefer that
    first = rows[0]
    if isinstance(first, dict) and "cnt" in first:
        return first.get("cnt")
    return first


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Optional path to config.ini passed to neo4j client")
    parser.add_argument("--ontology", default=os.path.join(os.path.dirname(__file__), "..", "schema", "ontology.json"),
                        help="Path to ontology.json")
    parser.add_argument("--dry-run", action="store_true", help="Print diagnostics and queries without executing against DB")
    args = parser.parse_args(argv)

    ont_path = os.path.abspath(os.path.expanduser(args.ontology))
    if not os.path.exists(ont_path):
        LOGGER.error("Ontology file not found: %s", ont_path)
        return 2

    ontology = load_ontology(ont_path)
    diagnostics = ontology.get("diagnostics", [])
    if not diagnostics:
        LOGGER.warning("No diagnostics found in %s", ont_path)
        return 0

    if args.dry_run:
        LOGGER.info("Dry run mode. The following diagnostics will be executed:")
        for d in diagnostics:
            LOGGER.info("- %s: %s", d.get("name"), d.get("query"))
        return 0

    # Create graph
    try:
        graph = make_graph_from_config(args.config)
    except Exception as e:
        LOGGER.exception("Failed to create Neo4j graph: %s", e)
        return 3

    failures = []
    LOGGER.info("Running %d diagnostics from %s", len(diagnostics), ont_path)
    for diag in diagnostics:
        name = diag.get("name") or diag.get("id") or "unnamed"
        try:
            val = run_diagnostic(graph, diag)
        except Exception as e:
            LOGGER.exception("Diagnostic '%s' failed to execute: %s", name, e)
            failures.append((name, "ERROR", str(e)))
            continue

        # Normalise numeric values where possible
        try:
            numeric = None
            if isinstance(val, (int, float)):
                numeric = val
            elif isinstance(val, str) and val.isdigit():
                numeric = int(val)
            elif isinstance(val, dict) and len(val) == 1:
                # try to extract first value
                numeric = next(iter(val.values()))
        except Exception:
            numeric = None

        min_expected = diag.get("min")
        max_expected = diag.get("max")

        ok = True
        if numeric is None:
            LOGGER.info("%s -> %s", name, val)
        else:
            LOGGER.info("%s -> %s (min=%s max=%s)", name, numeric, min_expected, max_expected)
            if min_expected is not None and numeric < min_expected:
                ok = False
            if max_expected is not None and numeric > max_expected:
                ok = False

        if not ok:
            failures.append((name, numeric, (min_expected, max_expected)))

    if failures:
        LOGGER.error("%d diagnostics failed:", len(failures))
        for f in failures:
            LOGGER.error(" - %s -> %s (expected min,max=%s)", f[0], f[1], f[2])
        return 4

    LOGGER.info("All diagnostics within configured thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
#!/usr/bin/env python3
"""Run schema diagnostics and assert thresholds for CI.

Reads `textgraphx/schema/ontology.json` diagnostics entries. Each diagnostic may include an
optional `min` and/or `max` numeric threshold. The script exits with code 0 when all asserts
pass; non-zero otherwise.

Usage:
    python -m textgraphx.tools.schema_asserts --config path/to/config.ini
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from textgraphx.tools.schema_validation import load_ontology, run_diagnostics, make_graph_from_config
import sys


def evaluate(diagnostics: dict, results: dict) -> int:
    failures = []
    for name, diag in diagnostics.items():
        res = results.get(name)
        if res is None:
            failures.append((name, "no result"))
            continue
        try:
            value = float(res)
        except Exception:
            failures.append((name, f"non-numeric result: {res}"))
            continue
        if "min" in diag and value < float(diag["min"]):
            failures.append((name, f"value {value} < min {diag['min']}"))
        if "max" in diag and value > float(diag["max"]):
            failures.append((name, f"value {value} > max {diag['max']}"))
    if failures:
        LOGGER.error("Schema asserts FAILED:")
        for name, msg in failures:
            LOGGER.error(" - %s: %s", name, msg)
        return 2
    LOGGER.info("Schema asserts OK")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None, help="Optional config.ini for Neo4j connection")
    args = p.parse_args()

    # locate ontology used by schema_validation
    ROOT = Path(__file__).resolve().parents[2]
    ontology_path = ROOT / "textgraphx" / "schema" / "ontology.json"
    if not ontology_path.exists():
        LOGGER.error("ontology.json not found at expected location: %s", ontology_path)
        sys.exit(1)

    ontology = load_ontology(ontology_path)
    diagnostics_list = ontology.get("diagnostics", [])

    # create driver/graph compat using project helper
    try:
        driver = make_graph_from_config(args.config)
    except Exception as e:
        LOGGER.exception("Failed to create Neo4j driver: %s", e)
        sys.exit(2)

    results = run_diagnostics(driver, diagnostics_list)

    # simplify results: if value is a dict with 'cnt', take it
    simplified = {}
    for k, v in results.items():
        if isinstance(v, dict) and "cnt" in v:
            simplified[k] = v["cnt"]
        else:
            simplified[k] = v

    # diagnostics_list contains entries with name and optional min/max
    diag_map = {d.get('name'): d for d in diagnostics_list}
    exit_code = evaluate(diag_map, simplified)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
