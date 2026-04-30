---
description: "Run the textgraphx M1–M10 evaluation suite against MEANTIME, compare to baselines, and produce a structured Markdown summary highlighting regressions, contract failures, and determinism status."
argument-hint: "optional: subset of milestones (e.g., M2,M4,M8) — defaults to full suite"
agent: "agent"
---

# Run MEANTIME Evaluation Cycle

You are running the textgraphx evaluation suite. Follow [evaluation.instructions.md](../instructions/evaluation.instructions.md) and [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](../../docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md).

## Inputs

- **Milestones to run** (default: all M1–M10)
- **Dataset slice** (default: full MEANTIME corpus under `src/textgraphx/datastore/dataset/`)
- **Baseline comparison** (default: yes)

## Steps

1. **Pre-flight**:
   - Confirm Neo4j is reachable (skip with explanation if not — most evaluators need a graph).
   - Confirm `src/textgraphx/datastore/annotated/` contains the gold annotations.
   - Capture environment metadata: Python version, spaCy version, Neo4j driver version, current git SHA.

2. **Run the evaluation harness**:
   ```bash
   python -m textgraphx.tools.evaluate_meantime \
       --output src/textgraphx/datastore/evaluation/latest/ \
       --milestones <list>
   ```
   (or the equivalent entry point — check `src/textgraphx/tools/` for the canonical CLI).

3. **Verify report validity** (M1):
   - Every report carries a validity header (`schema_version`, `run_id`, `run_metadata_hash`, `determinism_verified`, `created_at`, `tool_versions`).
   - If `determinism_verified=False`, **stop** and report the determinism failure — do not proceed to baseline comparison.

4. **Compare against baselines** (M9):
   - Use `src/textgraphx/evaluation/regression_detector.py` to diff `latest/` against `baseline/`.
   - For each milestone, report: metric, baseline value, current value, delta, regression/improvement flag.

5. **Check CI quality gates** (M10):
   - Run `python -m textgraphx.tools.check_quality_gate`.
   - Report any gate failures with the exact failing assertion.

6. **Produce a structured summary** in this format:

   ```markdown
   # MEANTIME Evaluation Report — <UTC timestamp>

   **Git SHA**: <sha>  •  **Run ID**: <run_id>  •  **Determinism**: ✅/❌

   ## Milestone Status
   | Milestone | Scope | Status | Notes |
   |-----------|-------|--------|-------|
   | M1 | Validity & determinism | ✅ | — |
   | M2 | Mention layer | ⚠️ regression | F1 0.82 → 0.79 |
   | ... | ... | ... | ... |

   ## Regressions (sorted by severity)
   - <metric>: <baseline> → <current> (delta <Δ>)

   ## Contract Failures (M4)
   - <phase>: <assertion> — <details>

   ## Recommendations
   - <actionable next steps>
   ```

7. **Do NOT** auto-update baselines. Baselines are a human contract — if a regression is intentional, the user must invoke the baseline-rotation procedure manually (see `evaluation.instructions.md` §5).

## Hard constraints

- Do not write evaluation artifacts outside `src/textgraphx/datastore/evaluation/`.
- Do not mutate `baseline/` files.
- Do not silence determinism failures.
- Do not commit `latest/` outputs unless the user explicitly requests it.
