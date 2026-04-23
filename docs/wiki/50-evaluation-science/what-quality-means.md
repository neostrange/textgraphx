<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# What Quality Means

**Gateway** · **Wiki Home** · **Evaluation Science** · What Quality Means

## Abstract

"Quality" for an event-centric temporal KG is not a single scalar. It splits along four axes: correctness, completeness, consistency, and provenance. A system can look strong on one axis while failing another.

## The four axes

1. **Correctness.** Does each extracted element (mention, entity, event, TIMEX, TLINK) match reality (or gold)?
2. **Completeness.** Are we missing mentions, events, or temporal links that should be there?
3. **Consistency.** Does the graph satisfy its reasoning contracts (span invariants, endpoint types, Allen-algebra)?
4. **Provenance.** Can every element be traced back to a token span, a rule, and a configuration?

## Why four axes, not one

- Precision/recall collapse axes 1+2 but say nothing about axis 3 or 4.
- A graph can be 100% span-correct and still contain contradictions that make downstream reasoning unsound.
- Provenance is what makes a regression reviewable — a metric drop you cannot trace is a science failure, not a system failure.

## How axes map to TextGraphX reports

| Axis | Primary artifact |
| --- | --- |
| Correctness | Per-phase P/R/F in `src/textgraphx/datastore/evaluation/` |
| Completeness | Coverage diagnostics in the same reports; per-document gold miss counts |
| Consistency | `temporal_reasoning_profile` contradiction/closure diagnostics |
| Provenance | `src/textgraphx/datastore/evaluation/<run>/meta.json` + self-certifying report footer |

## References

- [hur2024unifying]
- [hogan2021kg]
- [paulheim2017kg]

## See also

- [`meantime-bridge.md`](meantime-bridge.md)
- [`metrics-catalog.md`](metrics-catalog.md)
- [`known-limitations.md`](known-limitations.md)
- [`../55-evaluation-strategy/strategy-overview.md`](../55-evaluation-strategy/strategy-overview.md)
