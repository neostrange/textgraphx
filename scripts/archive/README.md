# scripts/archive

This directory holds **ad-hoc debug, patch, inspect, parse, and one-off fix scripts** that were written
during iterative development and debugging sessions.

They are kept here for historical reference and are **not actively maintained**. They should not be
imported, run as part of the pipeline, or referenced from production code.

If you need to recover logic from one of these scripts for a new feature, copy the relevant snippet
into the appropriate module under `src/textgraphx/` or `tools/`.

## Contents by prefix

| Prefix | Nature |
|---|---|
| `patch_*.py` | One-off Cypher/source patches applied during development |
| `fix_*.py` | Targeted repair scripts for specific graph or code states |
| `inspect_*.py`, `examine_*.py` | Ad-hoc graph inspection queries |
| `match_drag*.py` | Exploratory Cypher matching sessions |
| `parse_*.py` | Log and evaluation output parsers for specific debug cycles |
| `test_*.py` | Manual smoke tests (not part of the formal pytest suite in `tests/`) |
| `debug_*.py`, `temp_*.py` | Clearly temporary exploration scripts |
| `count_*.py`, `check_*.py` | Quick-count and sanity-check queries |
| `get_*.py`, `dump_*.py` | Data extraction helpers for specific debug runs |
| `summarize_*.py`, `print_*.py` | Report formatting helpers |
| `recover.py`, `restore_*.py` | Manual recovery scripts |
| `run_*.py`, `run_*.sh` | Ad-hoc pipeline invocations (not the canonical run scripts) |
