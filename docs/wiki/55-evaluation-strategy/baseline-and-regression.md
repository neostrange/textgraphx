<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Baseline and Regression

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Baseline & Regression

## Abstract

Every metric that matters has a committed baseline. Regression gates compare a fresh run's summary to that baseline and fail CI when a metric drops beyond threshold.

## Baseline storage

- Location: `src/textgraphx/datastore/evaluation/baseline/`.
- Format: JSON summaries, one per tracked phase/evaluator.
- Provenance: each baseline carries the commit, date, and dataset reference under which it was produced.

## Gate policy

- Default gate: non-degrading — a metric may move up, but a drop beyond the per-metric threshold fails the gate.
- Contract-violation counts are gated strictly: any increase above zero (when baseline is zero) is a failure.
- Advisory-violation counts produce warnings only.

## Updating a baseline

Updating a baseline is a reviewable change:

1. Land the underlying fix or model upgrade in a PR.
2. In the same or a follow-up PR, regenerate the affected baseline files and commit them alongside an explanation in `CHANGELOG.md`.
3. CI re-runs the gate against the new baseline. A maintainer sign-off is required.

No baseline update may silently mask a regression.

## References

- [hur2024unifying]

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`self-certifying-reports.md`](self-certifying-reports.md)
- [`known-error-modes.md`](known-error-modes.md)
