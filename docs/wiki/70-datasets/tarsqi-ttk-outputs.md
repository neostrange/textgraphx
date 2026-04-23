<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# TARSQI / TTK Outputs

**Gateway** · **Wiki Home** · **Datasets** · TARSQI / TTK

## Abstract

The TARSQI Toolkit (TTK) provides the temporal extraction machinery the temporal phase relies on. Its outputs feed directly into the TIMEX, Signal, and event-trigger layers of the graph.

## What TTK produces

- TIMEX expressions with ISO-TimeML attributes.
- Event trigger candidates.
- Signal candidates.
- Initial TLINK proposals (used selectively in TextGraphX; the rule engine is the authoritative TLINK source).

## How TextGraphX uses it

- [`src/textgraphx/TemporalPhase.py`](../../../src/textgraphx/TemporalPhase.py) wraps TTK and writes canonical `TIMEX`, `TimexMention`, and `Signal` nodes with spans aligned to the existing `TagOccurrence` layer.
- TTK's TLINK proposals are inspected but not passed through as-is; `TlinksRecognizer.py` is the contract-enforcing TLINK producer.

## Limits

- TTK is a rule-based system; recall on implicit temporal relations is inherently limited.
- Alignment between TTK tokenization and our token layer requires explicit mapping — coordinate discipline is enforced by [`../40-ontology-and-schema/span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md).

## References

- [tarsqi-ttk]
- [pustejovsky2003timeml]

## See also

- [`../30-algorithms/temporal-extraction-ttk.md`](../30-algorithms/temporal-extraction-ttk.md)
- [`../10-linguistics/temporal-semantics.md`](../10-linguistics/temporal-semantics.md)
