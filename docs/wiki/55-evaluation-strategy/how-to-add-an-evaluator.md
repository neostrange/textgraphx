<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# How to Add an Evaluator

**Gateway** · **Wiki Home** · **Evaluation Strategy** · How to Add an Evaluator

## Abstract

A new evaluator lands in four steps: declare its contract, implement the scoring, emit the standard report shape, and wire regression into the quality gate.

## 1. Declare the contract

- What layer does the evaluator cover? (token / entity / event / TLINK / contract / bridge)
- What is the input (graph scope, gold scope, configuration) and the output (metrics + diagnostics)?
- Is it deterministic? (it must be)
- Is it fast enough for per-PR CI, or scheduled only?

Add the entry to the metrics catalog: [`metrics-catalog.md`](metrics-catalog.md) and [`../50-evaluation-science/metrics-catalog.md`](../50-evaluation-science/metrics-catalog.md).

## 2. Implement scoring

- Place the evaluator under `src/textgraphx/evaluators/` with a clear module name.
- Reuse the shared report-writing helpers so the artifact shape is consistent.
- Do not write outputs anywhere outside `src/textgraphx/datastore/evaluation/`.

## 3. Emit the standard report shape

Every evaluator writes at least:

- A JSON summary: metrics, counts, contract violations, reproducibility metadata.
- A Markdown companion: human-readable view of the same content.
- A stable path pattern: `datastore/evaluation/<phase>/<date>-<run>/`.

## 4. Wire the regression gate

- Add a baseline snapshot under `datastore/evaluation/baseline/<phase>/`.
- Add metric thresholds in the quality-gate configuration consumed by `src/textgraphx/tools/check_quality_gate.py`.
- Open a PR; first commit must be landed with `baseline_seed=true` metadata so reviewers know it is the initial baseline.

## Documentation checklist

A new evaluator is not considered complete until:

- It appears in [`metrics-catalog.md`](metrics-catalog.md).
- Its contract and failure modes appear in [`known-error-modes.md`](known-error-modes.md) if it introduces new ones.
- The CHANGELOG entry references the phase and the baseline-seed PR.

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`baseline-and-regression.md`](baseline-and-regression.md)
- [`../../CONTRIBUTING.md`](../../../CONTRIBUTING.md)
