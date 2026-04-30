---
description: "Use when modifying the M1–M10 evaluation framework (src/textgraphx/evaluation/**) or running MEANTIME quality assessments. Covers validity headers, run-metadata hashing, baseline rotation, regression detection, and CI quality gates."
applyTo: "src/textgraphx/evaluation/**/*.py"
---

# textgraphx Evaluation Framework Guidelines (M1–M10)

## 1. The Milestone Map

| Milestone | Module | Scope |
|-----------|--------|-------|
| M1 | `report_validity.py`, `determinism.py` | Unified schema, run-metadata hashing, determinism |
| M2 | `mention_layer_evaluator.py` | Mention-layer quality |
| M3 | `edge_semantics_evaluator.py` | Edge-semantics quality |
| M4 | `phase_assertion_evaluator.py` | Phase-contract assertions |
| M5 | `semantic_category_evaluator.py` | Semantic-category quality |
| M6 | `legacy_layer_evaluator.py` | Legacy / backward-compat layer |
| M7 | `fullstack_harness.py` | End-to-end harness |
| M8 | `meantime_bridge.py` | MEANTIME alignment + cross-phase consistency |
| M9–M10 | `regression_detector.py`, `ci_integration.py` | Regression baselines + CI gates |

See [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](../../docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md) for the authoritative spec.

## 2. Validity Header (M1)

Every evaluation report **must** carry a validity header:

- `schema_version` — evaluation report schema version
- `run_id` — UUID per evaluation invocation
- `run_metadata_hash` — hash of (code SHA + config + dataset hashes)
- `determinism_verified` — boolean from `determinism.py`
- `created_at` — UTC ISO-8601 timestamp
- `tool_versions` — Python, spaCy, Neo4j driver, textgraphx package version

If any field is missing, the report is invalid and CI must reject it.

## 3. Output Locations (canonical, do not deviate)

| Path | Contents |
|------|----------|
| `src/textgraphx/datastore/evaluation/latest/` | Most recent evaluation results |
| `src/textgraphx/datastore/evaluation/baseline/` | Locked-in regression baselines |
| `src/textgraphx/datastore/annotated/` | Gold-standard MEANTIME annotations |
| `src/textgraphx/datastore/dataset/` | Evaluation input corpora |

**Never** write evaluation artifacts to the repo root. Files like `eval_*.json`, `single_eval.json`, `report.txt` at the repo root are mistakes — they belong in `datastore/evaluation/latest/` and must not be committed.

## 4. Determinism Verification (M1)

Before emitting a report:

1. Run the evaluator twice on the same input.
2. Compare output hashes.
3. If they differ, set `determinism_verified=False` and abort baseline updates.

Helpers in `evaluation/determinism.py`. Do not reimplement.

## 5. Baseline Rotation Policy (M9)

Baselines in `datastore/evaluation/baseline/` are **locked**. Updating one requires:

1. A justification (e.g., a deliberate model upgrade, a fixed bug that changes scores).
2. The previous baseline archived under `baseline/archive/<date>/`.
3. A CHANGELOG entry referencing the change.
4. A linked PR review by a second contributor.

**Never** auto-update baselines from CI. Baselines are a human contract.

## 6. Regression Detection (M9–M10)

`regression_detector.py` computes diffs between `latest/` and `baseline/`. CI quality gates (`ci_integration.py`) fail when:

- Any hard-contract metric **regresses** (drops below baseline minus tolerance)
- Any phase contract assertion fails (M4)
- Determinism verification fails

Tolerances are stored in the baseline; do not edit them inline in evaluator code.

## 7. MEANTIME Alignment (M8)

`meantime_bridge.py` is the canonical adapter between textgraphx outputs and MEANTIME gold annotations. When extending it:

- Preserve token offsets exactly — MEANTIME uses character spans; convert with documented helpers, not ad-hoc arithmetic.
- Never silently drop unmatched gold annotations — log them under the report's `unmatched_gold` field.
- Cross-phase consistency violations (e.g., a TLINK referencing a non-existent TEvent) are reported, not auto-fixed.

## 8. Adding a New Metric

1. Define the metric in the relevant milestone evaluator.
2. Add it to the unified schema (M1).
3. Establish a baseline by running on the gold corpus and committing to `baseline/` (with the policy in §5).
4. Wire it into `ci_integration.py` if it should be a quality gate.
5. Document in [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](../../docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md) and [docs/EVALUATION_DIAGNOSTICS.md](../../docs/EVALUATION_DIAGNOSTICS.md).

## 9. Reporting Discipline

- Reports are **JSON**, machine-readable first.
- Human-readable summaries are derived (CSV / Markdown) by tools in `tools/`, not authored.
- Floating-point metrics serialized to 4 decimal places to keep diffs stable.

## 10. Anti-patterns

- ❌ Writing eval artifacts outside `datastore/evaluation/`
- ❌ Auto-rotating baselines in CI
- ❌ Reporting a metric without a validity header
- ❌ Using wall-clock timestamps inside metric values (kills determinism)
- ❌ Silent fallbacks when MEANTIME parsing fails
