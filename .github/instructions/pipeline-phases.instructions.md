---
description: "Use when modifying or adding pipeline phase modules (src/textgraphx/pipeline/phases/**, pipeline/ingestion/**). Covers phase contracts, idempotency, completion markers, determinism, and orchestrator integration."
applyTo: "src/textgraphx/pipeline/**/*.py"
---

# textgraphx Pipeline Phase Guidelines

## 1. Phase Contract (mandatory)

Every phase **must** declare an explicit input/output contract. Contracts live alongside the phase module (e.g., docstring + `PHASE_CONTRACT` dict) and are validated by `evaluation/phase_assertion_evaluator.py`.

A contract specifies, at minimum:

- **Required input labels** — node types that must already exist in the graph
- **Produced labels** — node types this phase creates
- **Produced relationships** — edges this phase writes
- **Required properties** on produced nodes (`doc_id`, `start_tok`, `end_tok`, `text`, `source`, `confidence` where applicable)
- **Completion marker** — name written to the graph upon successful completion

If you change any of these, update the contract, the M4 phase-assertion test, and `docs/architecture-overview.md` in the same PR.

## 2. Idempotency

Every phase **must** be idempotent. Running the phase twice on the same input must produce identical graph state.

- Use `MERGE` over `CREATE` when writing nodes/relationships.
- Use deterministic IDs (document-content hash → stable integer fallback). **Never `uuid4()` or `random`.**
- Check the completion marker before re-running expensive work — but do not refuse to re-run; allow forced re-execution via orchestrator.

## 3. Completion Markers

On success, write a marker node (or property on `AnnotatedText`) recording:

- Phase name
- Phase version (bump when output schema changes)
- Run ID (provided by orchestrator)
- Timestamp (UTC, ISO-8601)

Example pattern:

```python
db.run("""
    MATCH (a:AnnotatedText {doc_id: $doc_id})
    MERGE (a)-[:HAS_PHASE_RUN]->(p:PhaseRun {phase: $phase, run_id: $run_id})
    SET p.version = $version, p.completed_at = $ts
""", doc_id=doc_id, phase=PHASE_NAME, run_id=run_id, version=PHASE_VERSION, ts=now_iso())
```

## 4. Determinism

- Process documents and sentences in **sorted order** (lexicographic by `doc_id`, then by `sent_idx`).
- Do not iterate Python sets or unordered dicts where output order affects graph state.
- Determinism is verified by `evaluation/determinism.py` — run it locally before merging.

## 5. Provenance

Every node and edge written by a phase carries a `source` property identifying:

- The phase that produced it (e.g., `"refinement.coreference"`)
- The technique tier (`T1_RULE`, `T2_ML`, `T3_LLM`)
- For LLM outputs, additionally a `model_id` and `prompt_version`

This is non-negotiable — provenance is a core differentiator (see `copilot-instructions.md` §1.1).

## 6. Tier Selection

When choosing how to extract something:

| Tier | Use first | Example |
|------|-----------|---------|
| **T1 — Deterministic rules** | Linguistic signal is structurally explicit | Cypher patterns over dependency trees |
| **T2 — Specialized ML** | T1 has poor recall | spaCy NER, SRL, coref |
| **T3 — LLMs** | T1 + T2 demonstrably underperform | Open-domain frame disambiguation |

Adding T3 calls **requires**:
- A justification comment citing T1/T2 limitations
- A deterministic fallback path when the LLM is unavailable
- Cost/latency budget noted in the phase docstring

## 7. Orchestrator Integration

Phases are invoked by `orchestration/orchestrator.py`. To register a new phase:

1. Implement `run(self, doc_id: str, run_context: RunContext) -> PhaseResult`.
2. Register in the orchestrator's phase manifest with explicit dependencies (which phases must precede it).
3. Add checkpoint hooks if the phase is expensive — see `orchestration/checkpoint.py`.

## 8. Mention vs Canonical Layer

Maintain the separation:

- Phases that produce surface forms write to mention labels (`NamedEntity`, `EventMention`, `TimexMention`).
- Phases that resolve identity write `REFERS_TO` edges to canonical labels (`Entity`, `TEvent`, `TIMEX`).
- Never collapse the two layers in a single write.

## 9. Imports

- Use canonical import paths: `from textgraphx.pipeline.phases.refinement import RefinementPhase`.
- **Do not** import from root-level shims (`GraphBasedNLP.py`, `RefinementPhase.py`, etc.) — those exist for backward compatibility only.

## 10. Anti-patterns

- ❌ Random IDs or non-deterministic ordering
- ❌ Writing to canonical labels without provenance
- ❌ Phases with implicit (undocumented) dependencies on prior phase output
- ❌ Skipping the completion marker
- ❌ Catching and silently swallowing Neo4j errors
- ❌ LLM calls without a deterministic fallback
