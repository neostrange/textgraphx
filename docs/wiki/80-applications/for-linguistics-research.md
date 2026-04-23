<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# For Linguistics Research

**Gateway** · **Wiki Home** · **Applications** · For Linguistics Research

## Abstract

The graph exposes linguistic layers (tokens, dependencies, SRL frames, coref chains, TIMEX/TLINK) in a queryable form that makes empirical studies tractable.

## Research-friendly properties

- Every mention carries span and document scoping.
- Mention-vs-canonical duality is preserved so studies of mention variation, pronominalization, and event coreference remain possible.
- Controlled vocabularies for event attributes and argument types make cross-document aggregation honest.
- The MEANTIME bridge gives a gold anchor for method comparison.

## Example studies supported

- Distribution of tense/aspect across event types by domain subset.
- Prevalence of narrative time-shifts signalled by particular temporal connectives.
- Participant-role realization patterns for nominal vs verbal predicates.
- Cross-document entity-chain topology under different coref backbones.

## Limits

- English-only current coverage.
- Rule-based temporal extraction limits recall on implicit relations; empirical claims must acknowledge this.

## References

- [palmer2005propbank]
- [fillmore2006framenet]
- [pustejovsky2003timeml]
- [cybulska2014meantime]
- [jurafsky-martin-slp]

## See also

- [`../10-linguistics/README.md`](../10-linguistics/README.md)
- [`../50-evaluation-science/known-limitations.md`](../50-evaluation-science/known-limitations.md)
