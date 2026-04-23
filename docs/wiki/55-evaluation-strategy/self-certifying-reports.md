<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Self-Certifying Reports

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Self-Certifying Reports

## Abstract

A self-certifying report is a single Markdown + JSON pair that declares: the commit used, the dataset identifier, every metric observed, every contract violated, and the result of the regression gate. It is the artifact a reviewer should be able to trust without rerunning anything.

## What a self-certifying report contains

- Run metadata: commit, date, hostname, dataset id, pipeline runtime mode.
- Pipeline assertions: pass/fail summary and every failing assertion in full.
- Per-phase metrics: aggregated and per-document.
- Contract diagnostics: hard-contract violations (must be zero) and advisory violations (informational).
- Regression gate outcome: per-metric delta against baseline, overall PASS/FAIL.
- Reproducibility footer: the exact commands that produced the report.

## Where reports live

- JSON + Markdown pair under `src/textgraphx/datastore/evaluation/<date>-<run>/`.
- A stable pointer file (e.g. `latest.json`) can be published by a CI job to support drill-down from the gateway.

## Why this format

- Reviewers do not have to rerun anything to audit a change.
- Every number comes with its provenance.
- Contract violations surface in the same document as metrics; a green metric cannot hide a broken invariant.

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`baseline-and-regression.md`](baseline-and-regression.md)
- [`../../archive/BACKLOG_ITEMS_4_9_AUDIT_REPORT.md`](../../archive/BACKLOG_ITEMS_4_9_AUDIT_REPORT.md)
