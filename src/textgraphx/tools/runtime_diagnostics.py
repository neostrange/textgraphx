"""Operator CLI for runtime diagnostics.

Examples:
  python -m textgraphx.tools.runtime_diagnostics --list-queries
  python -m textgraphx.tools.runtime_diagnostics --query phase_execution_summary
  python -m textgraphx.tools.runtime_diagnostics --totals-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from textgraphx.diagnostics import (
    get_registered_diagnostics,
    get_runtime_metrics,
    list_diagnostic_queries,
    run_registered_diagnostic,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List and execute TextGraphX runtime diagnostics.",
    )
    parser.add_argument(
        "--list-queries",
        action="store_true",
        default=False,
        help="List registered diagnostics query metadata and exit.",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Run one registered diagnostics query by stable name.",
    )
    parser.add_argument(
        "--totals-only",
        action="store_true",
        default=False,
        help="When running full diagnostics, emit only the aggregated totals block.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Payload is still printed to stdout.",
    )
    return parser


def _write_payload(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(payload, fh, indent=2)


def _emit_payload(payload: object, output: str | None) -> None:
    if output:
        _write_payload(Path(output), payload)
    print(json.dumps(payload, indent=2))


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_queries:
        _emit_payload(get_registered_diagnostics(), args.output)
        return 0

    if args.query and args.query not in list_diagnostic_queries():
        print(f"ERROR: unknown diagnostics query: {args.query}", file=sys.stderr)
        return 2

    from textgraphx.neo4j_client import make_graph_from_config

    graph = make_graph_from_config()
    close_fn = getattr(graph, "close", None)
    try:
        if args.query:
            payload = run_registered_diagnostic(graph, args.query)
        else:
            payload = get_runtime_metrics(graph)
            if args.totals_only and isinstance(payload, dict):
                payload = payload.get("totals", {})
        _emit_payload(payload, args.output)
        return 0
    finally:
        if callable(close_fn):
            close_fn()


if __name__ == "__main__":
    raise SystemExit(main())