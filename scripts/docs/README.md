# Docs Generators

Small, deterministic generators that produce auto-sync'd wiki pages from the code and schema. The output files carry an `AUTO-GENERATED` banner and must not be hand-edited.

| Script | Output | `--check` mode |
| --- | --- | --- |
| `generate_code_index.py` | `docs/wiki/99-references/code-index.md` | Exits non-zero if the committed file is stale. |
| `generate_schema_summary.py` | `docs/wiki/40-ontology-and-schema/schema-autogen.md` | Exits non-zero if the committed file is stale. |

## Local use

```bash
python scripts/docs/generate_code_index.py
python scripts/docs/generate_schema_summary.py
```

## CI

The forthcoming `.github/workflows/docs-guardrails.yml` (lands with PR-5) runs both generators in `--check` mode so stale docs block PR merge.
