---
description: "Generate a versioned, idempotent, reversible Neo4j schema migration in textgraphx, update the ontology, bump schema_version, and add a contract test."
argument-hint: "short description of the schema change (e.g., 'add Situation label')"
agent: "agent"
---

# Add a Schema Migration

You are creating a new schema migration for textgraphx. Follow [schema.instructions.md](../instructions/schema.instructions.md) and [cypher.instructions.md](../instructions/cypher.instructions.md).

## Inputs you should ask for (if not provided)

1. **Change description** (one line, present tense — "Add `Situation` label with required `frame_id`")
2. **Tier of affected element** (canonical / optional / legacy)
3. **Migration type** (additive / mutating / removal)
4. **Affected runtime modules** (which `pipeline/**` files write the impacted labels)
5. **Rollback plan** for `down()` — including any data loss

## Steps to perform

1. **Determine the next migration ID**
   - Inspect `src/textgraphx/schema/migrations/` for the highest `NNNN_*.py` number; increment by 1, zero-padded to 4 digits.

2. **Create the migration file** at `src/textgraphx/schema/migrations/NNNN_<short_snake>.py`:
   - Module docstring: change description, tier, motivation, references (issue / ADR if any)
   - `MIGRATION_ID`, `MIGRATION_VERSION` constants
   - `def up(db) -> None:` — idempotent forward Cypher (use `IF NOT EXISTS`, `MERGE`)
   - `def down(db) -> None:` — reversal Cypher; if destructive, raise a clear warning
   - All Cypher parameterized; no string interpolation

3. **Update `schema/ontology.yaml`** (human-authored source of truth):
   - Add/modify the label, relationship, or property
   - Mark the tier (canonical / optional / legacy)
   - Bump the top-level `schema_version`

4. **Regenerate `schema/ontology.json`** from the YAML (do not hand-edit JSON).

5. **Update [docs/schema.md](../../docs/schema.md)** with the new structure and an example.

6. **Add a contract test** at `src/textgraphx/tests/test_migration_NNNN.py`:
   - `@pytest.mark.unit @pytest.mark.contract`
   - Apply migration on a clean test graph; assert post-conditions
   - Apply migration **twice**; assert idempotency
   - Apply `down()`; assert state matches pre-migration

7. **Update CHANGELOG.md** under "Unreleased":
   ```
   ### Changed (or Added / Removed)
   - Schema migration NNNN: <change description>. See docs/schema.md.
   ```

8. **If the migration removes or renames a canonical element**, additionally:
   - Document the deprecation window
   - Inventory affected Cypher queries across `pipeline/**` and `tools/**`
   - Open follow-up tasks for query updates before the deprecation window closes

## Verification

```bash
pytest src/textgraphx/tests/test_migration_NNNN.py -v
pytest src/textgraphx/tests -m contract -q
```

If the migration touches canonical labels, also run:

```bash
pytest src/textgraphx/tests -m "unit or contract" -q
```

## Hard constraints (do not violate)

- Migrations must be **idempotent** and **reversible**
- Never edit `ontology.json` by hand
- Never bypass the migration system to alter schema directly in a phase module
- Never remove a legacy label without a deprecation window + query audit
