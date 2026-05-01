---
description: "Use when writing or reviewing Cypher queries (in Python strings, .cypher files, or schema migrations). Covers parameterization, MERGE vs CREATE, indexing, idempotency, and injection prevention."
applyTo: ["**/*.cypher", "src/textgraphx/**/*.py"]
---

# textgraphx Cypher Authoring Guidelines

> Applies to Cypher embedded in Python strings as well as standalone `.cypher` files.

## 1. Always Parameterize

**Never** interpolate values into Cypher strings. Always use parameters.

```python
# ✅ Correct
db.run(
    "MATCH (a:AnnotatedText {doc_id: $doc_id}) RETURN a",
    doc_id=doc_id,
)

# ❌ Wrong — Cypher injection risk + cache miss
db.run(f"MATCH (a:AnnotatedText {{doc_id: '{doc_id}'}}) RETURN a")
```

This is a security requirement (Cypher injection is real) **and** a performance requirement (parameterized queries hit the query cache).

## 2. MERGE vs CREATE

| Use | When |
|-----|------|
| `MERGE` | Default. Required for idempotent phase writes. |
| `CREATE` | Only when you have *just* verified non-existence in the same transaction, and want to fail loudly on duplicates. |

`MERGE` on a node requires a uniquely identifying property set. Document the constraint that backs the merge:

```cypher
// Backed by constraint: AnnotatedText.doc_id is unique
MERGE (a:AnnotatedText {doc_id: $doc_id})
ON CREATE SET a.created_at = $ts
```

## 3. Constraints & Indexes

- Uniqueness constraints for canonical identifiers (`doc_id`, composite keys for `Sentence`, `TagOccurrence`) are declared in `src/textgraphx/database/constraints.py` and applied via migrations.
- Lookup indexes for hot paths (e.g., `start_tok`, `end_tok` on mention nodes) live in the same place.
- Never create constraints ad-hoc inside a phase — it must go through a migration (see `schema.instructions.md`).

## 4. Property Hygiene

Required properties for canonical / mention nodes:

- `doc_id` — always
- `start_tok`, `end_tok` — for any span-bearing node (with `start_tok <= end_tok`)
- `text` — surface form
- `lemma` — where applicable
- `confidence` — for inferred/enriched nodes
- `source` — provenance (phase + tier; see `pipeline-phases.instructions.md` §5)

Never write a node missing its required properties. Hard contracts (M4) will fail.

## 5. Read/Write Separation

- Use `db.run()` for writes inside a transaction-scoped session.
- Use read-only sessions (`session.read_transaction(...)`) for evaluators and tools that should never mutate the graph.
- Tag query intent in comments when ambiguous.

## 6. Avoid Anti-Patterns

| Pattern | Problem |
|---------|---------|
| `MATCH (n) RETURN n` (no label) | Full DB scan. Always use a label and indexed property. |
| `MATCH ... DELETE n` without `DETACH` | Throws on relationships. Use `DETACH DELETE` when intent is clear. |
| Cartesian products from disjoint `MATCH` clauses | Performance cliff. Use `WHERE` joins or `WITH` chaining. |
| `LOAD CSV` from file paths in code | Not used in this project; use Python ingestion. |
| String concatenation of Cypher | Injection. See §1. |

## 7. Result Shape

- Return only the fields you consume. Avoid `RETURN *`.
- Aliased returns: `RETURN n.doc_id AS doc_id, count(*) AS n` — explicit and stable.
- For metrics, return scalars or small maps; do not return whole nodes when an `id()` or property suffices.

## 8. Determinism

When ordering matters (almost always for graph-builder phases):

```cypher
MATCH (s:Sentence {doc_id: $doc_id})
RETURN s ORDER BY s.sent_idx ASC
```

Never rely on Neo4j's natural order. Always `ORDER BY` an indexed, total-ordered property.

## 9. Long Queries

For multi-clause queries (>15 lines), prefer a triple-quoted Python string with leading `//` comments per logical block, or move to a `.cypher` file alongside the module.

## 10. Migration Queries

Migration Cypher must be:

- Idempotent (`CREATE INDEX IF NOT EXISTS`, `MERGE`, conditional `MATCH ... WHERE NOT EXISTS`)
- Safe to interrupt and re-run
- Documented in the migration file's docstring with the rollback Cypher in `down()`

See `schema.instructions.md` for the full migration protocol.
