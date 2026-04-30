---
description: "Scaffold a new pipeline phase in textgraphx with phase contract, idempotent implementation, completion marker, contract tests, documentation update, and CHANGELOG entry."
argument-hint: "phase name (snake_case) and one-line responsibility"
agent: "agent"
---

# Add a New Pipeline Phase

You are scaffolding a new phase for the textgraphx pipeline. Follow the conventions in [pipeline-phases.instructions.md](../instructions/pipeline-phases.instructions.md) and [copilot-instructions.md](../copilot-instructions.md).

## Inputs you should ask for (if not provided)

1. **Phase name** (snake_case, e.g. `causal_link_recognizer`)
2. **One-line responsibility** (e.g. "Detect cause/effect TLINK refinements between TEvents")
3. **Tier** (T1 deterministic / T2 specialized ML / T3 LLM — must justify if T3)
4. **Predecessor phase(s)** (which phases must run first)
5. **Produced labels and relationships**
6. **Required input labels**

## Steps to perform

1. **Create the phase module** at `src/textgraphx/pipeline/phases/<phase_name>.py` with:
   - Module docstring summarizing responsibility, tier, predecessors
   - `PHASE_NAME`, `PHASE_VERSION` constants
   - `PHASE_CONTRACT` dict with `requires`, `produces_labels`, `produces_relationships`, `required_properties`, `completion_marker`
   - A `Phase` class implementing `run(self, doc_id: str, run_context) -> PhaseResult`
   - Idempotent Cypher writes using `MERGE` with deterministic IDs
   - Completion marker write at the end of `run()`
   - `source` provenance property on every node and edge

2. **Register the phase** in `src/textgraphx/orchestration/orchestrator.py`:
   - Add to the phase manifest with explicit dependencies on predecessors

3. **Add the phase contract test** at `src/textgraphx/tests/test_<phase_name>_contract.py`:
   - `@pytest.mark.unit @pytest.mark.contract`
   - Builds a minimal fixture graph
   - Runs the phase
   - Asserts produced labels/relationships match `PHASE_CONTRACT`
   - Asserts idempotency (run twice → identical state)
   - Asserts the completion marker is present

4. **Add a regression test stub** at `src/textgraphx/tests/test_<phase_name>_regression.py`:
   - `@pytest.mark.regression`
   - Compares a small evaluation against a baseline (placeholder until baseline established)

5. **Update documentation**:
   - Add a row to the pipeline stages table in [docs/architecture-overview.md](../../docs/architecture-overview.md)
   - Document the contract in [docs/schema.md](../../docs/schema.md) if new labels/relationships are introduced
   - Update [docs/PIPELINE_INTEGRATION.md](../../docs/PIPELINE_INTEGRATION.md)

6. **Update CHANGELOG.md** with an entry under "Unreleased":
   ```
   ### Added
   - New pipeline phase `<phase_name>`: <responsibility>. See docs/architecture-overview.md.
   ```

7. **If new labels or relationships are introduced**, additionally invoke the schema-migration prompt — do not edit the ontology in this prompt.

## Output expectations

- Use canonical import paths (no root-level shims)
- Use `MERGE` not `CREATE` for graph writes
- All IDs deterministic (document hash → integer fallback); never `uuid4()` or `random`
- Process inputs in sorted order
- Provenance `source` property on everything written

## Verification

After scaffolding, run:

```bash
pytest src/textgraphx/tests/test_<phase_name>_contract.py -v
pytest src/textgraphx/tests -m "unit and contract" -q
```

Report any contract test failures and fix before declaring the phase complete.
