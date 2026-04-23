<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Evaluation Strategy — Overview

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Overview

## Abstract

Evaluation in TextGraphX is organized in four tiers so "did it work?" becomes a mechanical, CI-enforced answer at every layer of the graph. Each tier has its own signals, failure modes, and owners.

## The four tiers

1. **Phase assertions (M1–M7).** Intra-phase invariants. Cheap, deterministic. Run on every pipeline execution.
2. **Per-phase evaluators.** Compare stage output against gold (MEANTIME subset, TempEval, etc.). Produce docs/summary artifacts under `src/textgraphx/datastore/evaluation/`.
3. **MEANTIME bridge validator (M8).** Structural gold alignment — does the system's canonical graph match the gold structure, regardless of surface spans?
4. **Regression gates (M9–M10).** Baseline snapshot comparison enforced in CI (`src/textgraphx/tools/check_quality_gate.py`).

## Where evaluation artifacts live

- Per-run outputs: `src/textgraphx/datastore/evaluation/` (never in `datastore/annotated/`).
- Baselines: `src/textgraphx/datastore/evaluation/baseline/`.
- Reports rendered into `evaluation_reports/` when a run requests it.

## Strategy principles

- **Deterministic by default.** Same input → same numbers.
- **Contract-before-metric.** A contract violation is a hard failure even if precision/recall look fine.
- **Tiered severity.** Hard contract vs advisory vs informational. See [`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md).
- **No silent baseline drift.** Quality gates fail closed; human approval is required to move a baseline.

## How this relates to the origin paper

The origin paper reported metrics on MEANTIME but did not encode phase assertions, a structural bridge validator, or CI-enforced regression gates. Those are TextGraphX additions. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## See also

- [`metrics-catalog.md`](metrics-catalog.md)
- [`evaluation-run-modes.md`](evaluation-run-modes.md)
- [`baseline-and-regression.md`](baseline-and-regression.md)
- [`self-certifying-reports.md`](self-certifying-reports.md)
- [`known-error-modes.md`](known-error-modes.md)
- [`how-to-add-an-evaluator.md`](how-to-add-an-evaluator.md)
- [`../50-evaluation-science/README.md`](../50-evaluation-science/README.md)

## References

- [hur2024unifying]
- [verhagen2007tempeval]
- [uzzaman2013tempeval3]
- [cybulska2014meantime]
