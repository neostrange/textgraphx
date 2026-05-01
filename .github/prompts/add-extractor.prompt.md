---
description: "Scaffold a new extractor (entity, event, relation, temporal, frame, etc.) in textgraphx, selecting the correct tier (T1 deterministic / T2 specialized ML / T3 LLM) with a deterministic fallback path."
argument-hint: "what to extract (e.g., 'causal connectives', 'organization mentions')"
agent: "agent"
---

# Add an Extractor

You are adding a new extractor to textgraphx. Follow the tiered methodology in [copilot-instructions.md](../copilot-instructions.md) §3 and the phase rules in [pipeline-phases.instructions.md](../instructions/pipeline-phases.instructions.md).

## Inputs you should ask for (if not provided)

1. **What is being extracted** (concept + linguistic signal)
2. **Where it attaches in the graph** (which existing labels gain a new edge or property)
3. **Tier candidate** — start at T1; only escalate with justification
4. **Evaluation signal** — which milestone(s) will measure this extractor (likely M2, M3, or M5)

## Tier Decision Protocol

Before writing any code, answer in writing:

| Question | If yes → |
|----------|----------|
| Is the linguistic signal structurally explicit (dependency pattern, lexical trigger, POS sequence)? | **T1** — Cypher / dependency rule |
| Does T1 give acceptable precision but poor recall? | **T2** — specialized ML model (spaCy component, classifier) |
| Have T1 + T2 been benchmarked and demonstrably underperform? | **T3** — LLM with deterministic fallback |

If you choose T3, the prompt **must** include:
- A justification comment citing T1/T2 limitations and the benchmark you ran
- A deterministic fallback path (the T1/T2 implementation, used when LLM is unavailable or returns invalid output)
- A `model_id` and `prompt_version` recorded as provenance on every node/edge produced
- A cost/latency budget noted in the docstring

## Steps

1. **Place the extractor** in the right location:
   - Inside an existing phase if it extends current behavior (`pipeline/ingestion/text_processing_components/` or `pipeline/phases/`)
   - As a standalone phase if it produces new labels/relationships → use `add-pipeline-phase.prompt.md` instead

2. **Implement the chosen tier**:
   - **T1**: Cypher pattern or dependency-tree rule. No external models.
   - **T2**: Wrap the model behind a small interface; cache the loaded model at module level; never load per-call.
   - **T3**: Use a thin LLM client; structured output (JSON schema) only; **always validate** the response before writing to the graph; on validation failure, fall back to T1/T2.

3. **Provenance** — every node/edge written carries:
   - `source` = `"<phase>.<extractor>"`
   - `tier` = `"T1_RULE"` / `"T2_ML"` / `"T3_LLM"`
   - For T3: `model_id`, `prompt_version`, `confidence`

4. **Tests**:
   - `@pytest.mark.unit` for the extractor logic on synthetic input
   - `@pytest.mark.contract` if it writes to canonical labels
   - For T3: a mock test verifying the deterministic fallback fires when the LLM returns invalid output

5. **Evaluation hook**:
   - Add metrics to the relevant milestone evaluator (M2 / M3 / M5)
   - Establish a baseline only after stabilization (do not commit a baseline that swings every run)

6. **Documentation**:
   - Add a brief entry under the relevant phase in [docs/architecture-overview.md](../../docs/architecture-overview.md)
   - If T3, additionally document the prompt and validation schema in `docs/` (alongside the prompt version)

7. **CHANGELOG.md** entry under "Unreleased".

## Hard constraints

- Default to T1. Escalation requires written justification.
- T3 without a deterministic fallback is rejected.
- LLM API keys never appear in the repo. Read from environment.
- All extractors must be deterministic at the graph-write boundary (same input → same graph state).

## Example tier-decision comment to include in code

```python
# Tier decision: T2 (spaCy NER)
# - T1 (regex on capitalized tokens) gave precision 0.91 / recall 0.42 on MEANTIME dev split.
# - T2 (en_core_web_trf) gave precision 0.93 / recall 0.86 — adopted.
# - T3 not evaluated; T2 meets the M2 quality bar.
```
