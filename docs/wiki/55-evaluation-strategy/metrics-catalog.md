<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Metrics Catalog (Strategy)

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Metrics Catalog

## Abstract

The metrics the system routinely reports, with their scope, and the tier they belong to. See also the science-side catalog at [`../50-evaluation-science/metrics-catalog.md`](../50-evaluation-science/metrics-catalog.md).

## Layer-wise metrics

| Layer | Primary metric | Secondary signals |
| --- | --- | --- |
| Tokens / dependencies | Pass/fail on phase assertions | Parse-label coverage |
| NER / EntityMentions | Span precision/recall/F1 (exact and relaxed) | Type-confusion matrix |
| Coreference | B³, CEAF, MUC (when gold chains are available) | Mention detection P/R/F |
| SRL / Frames | Frame-level P/R/F, argument-role P/R/F | Predicate coverage |
| TIMEX | Span P/R/F, value-accuracy | Type confusion |
| Events (TEvent / EventMention) | Event-trigger P/R/F, attribute accuracy | Nominal-vs-verbal breakdown |
| Event participants | Participant P/R/F with role typing | Missing-participant rate |
| TLINK | Relation-type P/R/F over canonical reltypes | Consistency score, contradiction count, closure-inflation |
| Schema/contracts | Contract-violation count | Advisory-violation count |
| Regression | Delta vs baseline, per metric | Pass/fail threshold per metric |

## Aggregation rules

- Per-document reports always include counts alongside rates.
- Summary reports aggregate with micro-averaging by default; macro-averages are reported when doc-skew matters.
- Baseline comparison reports always show both absolute and delta values.

## References

- [verhagen2007tempeval]
- [verhagen2010tempeval2]
- [uzzaman2013tempeval3]
- [tjong2003conll]

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`../50-evaluation-science/metrics-catalog.md`](../50-evaluation-science/metrics-catalog.md)
