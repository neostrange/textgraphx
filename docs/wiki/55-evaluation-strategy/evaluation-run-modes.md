<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Evaluation Run Modes

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Run Modes

## Abstract

The pipeline and evaluators expose a small number of run modes. Each has an intended audience and a different strictness contract.

## Pipeline runtime modes

- **`testing`** — clears and rebuilds the graph before each run; relaxed on pre-existing data.
- **`production`** — fails fast if the target DB already contains documents; guarantees clean provenance.

Both modes enforce the hard-contract scope declared in `ontology.json`.

## Evaluator run modes

- **Phase evaluation.** Runs per-phase checks and writes a per-document JSON + a run summary. Artifacts under `src/textgraphx/datastore/evaluation/<phase>/`.
- **Bridge evaluation.** Runs the MEANTIME bridge validator. See [`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md).
- **Regression gate.** Compares a completed run's summary to the current baseline under `src/textgraphx/datastore/evaluation/baseline/`. Implemented by `src/textgraphx/tools/check_quality_gate.py`.
- **Self-certifying report.** Full end-to-end run that emits a single human-readable report (Markdown) alongside the JSON summary.

## Local vs CI

- **Local.** Engineers run evaluators by hand before opening a PR; outputs live under the evaluation tree only.
- **CI.** Structure guardrails (existing) + docs guardrails (new in this PR) + regression gate (existing). Data-heavy evaluators are typically gated to a scheduled run rather than every PR.

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`baseline-and-regression.md`](baseline-and-regression.md)
- [`self-certifying-reports.md`](self-certifying-reports.md)
