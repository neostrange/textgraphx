"""Schema validation script.

Runs a set of diagnostic count queries against a Neo4j instance using the
project's centralized Neo4j client (`textgraphx.neo4j_client`). The diagnostics
are loaded from `textgraphx/schema/ontology.json`.

Usage:
    python -m textgraphx.tools.schema_validation

Or run directly from the workspace python interpreter:
    python textgraphx/tools/schema_validation.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# ensure package imports work when script is executed directly from project root
ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from textgraphx.database.client import make_graph_from_config
import logging

logger = logging.getLogger(__name__)


def load_ontology(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_diagnostics(graph_compat, diagnostics: list[dict[str, str]]):
    results = {}
    for diag in diagnostics:
        name = diag.get("name")
        query = diag.get("query")
        try:
            # BoltGraphCompat.run(...).data() returns list-of-dicts, take first row's cnt if present
            data = graph_compat.run(query, {})
            rows = data.data()
            cnt = None
            if rows:
                # take first row, take any value named 'cnt' or the first value
                first = rows[0]
                if isinstance(first, dict) and "cnt" in first:
                    cnt = first["cnt"]
                else:
                    # pick first value
                    cnt = next(iter(first.values()), None)
            results[name] = cnt
        except Exception as e:
            results[name] = f"ERROR: {e}"
    return results


def pretty_print_results(results: dict[str, Any]):
    logger.info("Schema validation results:")
    for k, v in results.items():
        logger.info("  %s: %s", k, v)


def main(config_path: str | None = None):
    if config_path is None:
        config_path = None
    try:
        driver = make_graph_from_config(config_path)
    except Exception as e:
        logger.exception("Failed to create Neo4j driver from config: %s", e)
        logger.info("Provide a config.ini with [py2neo] or [neo4j] section, or ensure NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD are set in env.")
        raise

    # load ontology diagnostics
    ontology_path = ROOT / "textgraphx" / "schema" / "ontology.json"
    if not ontology_path.exists():
        logger.error("Cannot find ontology diagnostics at: %s", ontology_path)
        return 2

    ontology = load_ontology(ontology_path)
    diagnostics = ontology.get("diagnostics", [])

    logger.info("Running schema diagnostics against Neo4j...")
    results = run_diagnostics(driver, diagnostics)
    pretty_print_results(results)

    return 0


if __name__ == "__main__":
    # Optional argument: path to config.ini
    cfg = sys.argv[1] if len(sys.argv) > 1 else None
    exit(main(cfg))
