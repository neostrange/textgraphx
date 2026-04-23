<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — Temporal Extraction (TARSQI TTK)

**Gateway** · **Wiki Home** · **Algorithms** · Temporal Extraction (TTK)

## Purpose

Identify time expressions, temporal signals, and event triggers using TARSQI-style rules and write them into the graph with ISO-TimeML attributes.

## Inputs

- `TagOccurrence` sequence with POS + dependencies.
- Document creation time (DCT) when available.

## Outputs

- `TIMEX` canonical nodes + `TimexMention` evidence nodes + `REFERS_TO` edges.
- `Signal` nodes for temporal connectives (before, after, while, during, ...).
- Event trigger candidates passed to the event enrichment phase.

## Assumptions

- ISO-TimeML conventions for `type` / `value` / `mod` / `functionInDocument`.
- DCT is the default anchor for deictic expressions per `temporal_reasoning_profile.dct_anchor_policy`.

## Limits / failure modes

- Narrative time-shifts (flashbacks, hypotheticals) are only partially modeled.
- Relative-time expressions without a DCT may be left unresolved; evaluators flag these rather than guess.

## Implementation

- [`src/textgraphx/TemporalPhase.py`](../../../src/textgraphx/TemporalPhase.py).

## Evaluation

- TIMEX-level evaluator under `src/textgraphx/evaluators/`.
- Signal coverage checks (diagnostic query pack).

## References

- [pustejovsky2003timeml]
- [iso24617-1-2012]
- [tarsqi-ttk]
- [uzzaman2013tempeval3]

## See also

- [`../10-linguistics/temporal-semantics.md`](../10-linguistics/temporal-semantics.md)
- [`tlink-rule-engine.md`](tlink-rule-engine.md)
