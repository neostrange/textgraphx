---
description: "Use when modifying schema, ontology, or migration files (src/textgraphx/schema/**). Covers schema authority precedence, migration creation rules, ontology editing protocol, and version coordination."
applyTo: "src/textgraphx/schema/**"
---

# textgraphx Schema & Ontology Guidelines

## 1. Authority Precedence (read first)

When schema statements conflict, the **higher-precedence source wins**:

1. Runtime write paths (`pipeline/ingestion/`, `pipeline/phases/`)
2. Applied migrations (`schema/migrations/`)
3. [docs/schema.md](../../docs/schema.md)
4. `schema/ontology.json`
5. Historical / explanatory documentation

If you change a label, relationship, or required property, you must update **all** of the above that mention it — in the same PR.

## 2. Three-Tier Schema Model

| Tier | Meaning | Removal policy |
|------|---------|----------------|
| **Canonical** | Required for runtime + evaluation; CI-blocking | Only via versioned migration + coordinated query updates |
| **Optional** | Enrichment / observability signals; advisory | Migration recommended but not required |
| **Legacy** | Preserved during a migration window | Removed only after the migration window closes |

When introducing a new label or relationship, declare its tier explicitly in `ontology.json` and document the rationale.

## 3. Migration Rules

Every schema change requires a migration file in `src/textgraphx/schema/migrations/`:

- **Naming**: `NNNN_<short_description>.py` (zero-padded 4-digit sequence, no gaps)
- **Idempotent**: Re-running must be a no-op (`MERGE`, conditional `CREATE INDEX IF NOT EXISTS`, etc.)
- **Reversible**: Provide both `up()` and `down()`. If `down()` is destructive (drops data), document it loudly.
- **Tested**: Each migration ships with at least one `@pytest.mark.contract` test verifying post-migration invariants.
- **Tracked**: Append the migration ID to the schema version registry (see existing migrations for the pattern).

## 4. Ontology Editing Protocol

`schema/ontology.json` and `schema/ontology.yaml` must stay in sync:

1. Edit `ontology.yaml` first (human-authored).
2. Regenerate `ontology.json` via `python -m textgraphx.tools.regenerate_ontology` (or the equivalent script in `tools/`).
3. Bump the `schema_version` field.
4. Update [docs/schema.md](../../docs/schema.md) and [docs/ontology.yaml](../../docs/ontology.yaml) (the public-facing copy).
5. Add a CHANGELOG entry referencing the migration ID and updated docs.

## 5. Hard Contracts (CI-blocking)

Never weaken these without an explicit migration + ADR:

- `doc_id` present and consistent on all document-scoped nodes
- Referential integrity: `Mention → REFERS_TO → Entity / TEvent / TIMEX`
- Required core fields on canonical labels (see ontology)
- Span integrity: `start_tok <= end_tok`

## 6. Naming Conventions

- **Node labels**: `PascalCase`, singular (`NamedEntity`, not `named_entities`).
- **Relationships**: `SCREAMING_SNAKE_CASE`, verb or verb phrase (`REFERS_TO`, `HAS_TOKEN`).
- **Properties**: `snake_case`, descriptive (`start_tok`, `confidence`, `source`).
- **Mention vs canonical**: keep them distinct (e.g., `NamedEntity` mention layer, `Entity` canonical layer).

## 7. Avoid Inventing Vocabulary

When introducing concepts that have established academic frameworks (situations, scenarios, procedures, frames), align labels to one citable framework rather than creating bespoke names. See §11.3 of `copilot-instructions.md`.

## 8. Anti-patterns

- ❌ Editing `ontology.json` by hand without updating `ontology.yaml`
- ❌ Adding a label to runtime code without a migration
- ❌ Repurposing an existing relationship type with new semantics
- ❌ Squashing migrations after they have shipped
- ❌ Removing a legacy label without a deprecation window and query audit
