---
description: "Use when writing or modifying pytest tests for textgraphx (test_*.py files in src/textgraphx/tests/). Covers markers, fixtures, mocking vs live Neo4j, contract assertions, determinism checks, and golden baselines."
applyTo: "src/textgraphx/tests/**/*.py"
---

# textgraphx Test Authoring Guidelines

## 1. Required Marker

Every test function **must** declare at least one marker:

| Marker | Use for |
|--------|---------|
| `@pytest.mark.unit` | Pure-Python, no I/O, no DB. Default for component logic. |
| `@pytest.mark.integration` | Touches external systems (Neo4j, file system). |
| `@pytest.mark.regression` | Locks in behavior against a golden baseline. |
| `@pytest.mark.scenario` | End-to-end orchestration through `PipelineOrchestrator`. |
| `@pytest.mark.orchestration` | Orchestrator-internal (checkpointing, run-history). |
| `@pytest.mark.slow` | Excluded from pre-merge runs; opt-in only. |

If a test exercises a hard-contract invariant (§5.4 of `copilot-instructions.md`), additionally tag it `@pytest.mark.contract`.

## 2. Neo4j Strategy

- **Default to mocking.** Use `pytest-mock` (`mocker` fixture) for `Neo4jConnection` / `db_interface`. Live Neo4j is a privilege, not a default.
- If a test genuinely requires live Neo4j, mark it `@pytest.mark.integration` **and** wrap connection setup in a fixture that skips when Neo4j is unreachable:
  ```python
  @pytest.fixture
  def live_neo4j(neo4j_connection):
      try:
          neo4j_connection.run("RETURN 1")
      except Exception:
          pytest.skip("Live Neo4j not available")
      return neo4j_connection
  ```
- Never hardcode connection credentials. Read from environment / fixture.

## 3. Determinism

- For any test that builds a graph, assert that **two runs produce identical IDs and identical edge sets**. Use helpers in `evaluation/determinism.py`.
- Never seed randomness inside a test to "make it deterministic" — fix the upstream non-determinism in the code under test.

## 4. Contract Tests

When asserting hard contracts (`doc_id` consistency, `Mention → REFERS_TO → Entity`, `start_tok <= end_tok`), prefer Cypher-based assertions over Python loops:

```python
@pytest.mark.unit
@pytest.mark.contract
def test_all_mentions_refer_to_canonical(graph_fixture):
    orphans = graph_fixture.run("""
        MATCH (m:NamedEntity) WHERE NOT (m)-[:REFERS_TO]->(:Entity)
        RETURN count(m) AS n
    """).single()["n"]
    assert orphans == 0
```

## 5. Golden Baselines

- Baselines live in `src/textgraphx/datastore/evaluation/baseline/`.
- Regression tests load the baseline, run the current pipeline, and assert structural equivalence.
- **Never** overwrite a baseline silently. Baselines are updated only via an explicit script (`scripts/update_baselines.py` — see CHANGELOG entry on baseline rotation policy).

## 6. Fixtures & Test Data

- Shared fixtures live in `src/textgraphx/tests/conftest.py` and `src/textgraphx/fixtures/`.
- Reference bundled corpora via the canonical datastore paths:
  - `src/textgraphx/datastore/dataset` — evaluation inputs
  - `src/textgraphx/datastore/annotated` — gold annotations
- **Do not** hardcode absolute paths or paths outside `src/textgraphx/datastore/`.

## 7. Naming & Structure

- File: `test_<module_name>.py`
- Function: `test_<behavior>__<condition>` (double underscore separates behavior and condition).
- Group related tests in `class Test<Behavior>:` only when sharing fixtures or reducing parametrize repetition.

## 8. Anti-patterns

- ❌ Tests that depend on execution order
- ❌ `time.sleep()` to "wait for Neo4j" — use a polling fixture instead
- ❌ Asserting on log output instead of return values / graph state
- ❌ Catching broad `Exception` in tests (mask real failures)
- ❌ Committing fixture changes without updating affected golden baselines

## 9. Quick Commands

```bash
# During development
pytest src/textgraphx/tests -k "<keyword>" -v

# Pre-commit smoke
pytest src/textgraphx/tests -m "unit or contract" -q

# Pre-merge
pytest src/textgraphx/tests -m "not slow" -q
```

See [src/textgraphx/tests/README_TESTS.md](../../src/textgraphx/tests/README_TESTS.md) for fixture catalog.
