"""Run Cypher migration scripts in `textgraphx/schema/migrations`.

This simple runner applies `.cypher` files in lexical order. It uses the
centralized `neo4j_client.make_graph_from_config()` to open a session so it
respects the same config precedence as the rest of the project.

Usage:
    python -m textgraphx.tools.run_migrations [path/to/config.ini]
"""
import os
import sys
from pathlib import Path

from textgraphx.neo4j_client import make_graph_from_config
import logging

logger = logging.getLogger(__name__)


def _find_migrations(root: Path):
    migrations_dir = root / "schema" / "migrations"
    if not migrations_dir.exists():
        return []
    files = sorted([p for p in migrations_dir.iterdir() if p.suffix in (".cypher", ".cyp")])
    return files


def run_migrations(config_path: str | None = None):
    repo_root = Path(__file__).resolve().parents[1]
    graph = make_graph_from_config(config_path)
    migrations = _find_migrations(repo_root)
    if not migrations:
        logger.info("No migration scripts found, nothing to do.")
        return 0

    for m in migrations:
        logger.info("Applying migration: %s", m.name)
        raw = m.read_text()
        # Remove single-line comments that start with -- and split into statements.
        lines = [l for l in raw.splitlines() if not l.strip().startswith("--")]
        cleaned = "\n".join(lines)
        # Split on semicolon to avoid sending multi-statement payloads to the driver
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        for stmt in statements:
            # Use the compatibility wrapper which will open/close a session per run
            try:
                graph.run(stmt)
            except Exception as e:
                # Log and continue so idempotent runs don't abort on existing constraints/indexes
                logger.warning("migration statement failed: %s", e)
        logger.info("Applied: %s", m.name)

    logger.info("All migrations applied.")
    return 0


if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_migrations(cfg))
