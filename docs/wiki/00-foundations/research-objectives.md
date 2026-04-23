<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Research Objectives

**Gateway** · **Wiki Home** · **Foundations** · Research Objectives

## Abstract

TextGraphX exists to investigate how far a pipeline-based, contract-governed LPG can go as a substrate for event-centric temporal reasoning over unstructured text. This page enumerates the research questions the system is built to answer and the measurable signals that indicate progress.

## Primary research questions

1. **RQ-1 Unified context.** Can a single LPG represent linguistic, referential, and temporal layers without forcing lossy projections for downstream reasoning?
2. **RQ-2 Contract-first extraction.** Do machine-readable schema/reasoning contracts catch more real failures than narrative documentation alone?
3. **RQ-3 Temporal consistency.** How often do observed TLINK sets violate Allen-algebra consistency in realistic corpora, and what closure policy minimizes lost information while blocking contradictions?
4. **RQ-4 Mention/canonical duality.** What invariants must hold between mention layers and canonical entities/events for downstream event-coref and timeline construction to remain sound?
5. **RQ-5 Regression-safe linguistic systems.** Can a linguistic pipeline be held to the same CI-enforced regression standard as a typical software system?

## Secondary questions

- Is GraphRAG-style retrieval materially improved when the underlying KG carries event-centric temporal structure rather than flat entity triples?
- What is the right granularity of "phase assertions" — per-document, per-phase, or per-contract?
- How do we best separate deprecated schema from active schema so queries and consumers degrade gracefully during migrations?

## Measurable signals

| Signal | Where it lives |
| --- | --- |
| Phase assertion pass rate | Evaluator reports under `src/textgraphx/datastore/evaluation/` |
| TLINK consistency score | Temporal evaluator + `temporal_reasoning_profile` |
| MEANTIME-gold alignment | [`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md) |
| Regression deltas vs baseline | `src/textgraphx/tools/check_quality_gate.py` |
| Contract violation counts | `diagnostics` section of `ontology.json` |

## Non-goals

- Replacing a general-purpose temporal reasoner.
- End-to-end neural extraction without structural validation.
- Multilingual parity; current work focuses on English corpora (MEANTIME English subset).

## References

- [hur2024unifying]
- [hogan2021kg]
- [paulheim2017kg]
- [cybulska2014meantime]

## See also

- [`theme-and-rationale.md`](theme-and-rationale.md)
- [`../60-research/open-questions.md`](../60-research/README.md)
