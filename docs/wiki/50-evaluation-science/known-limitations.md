<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Known Limitations (Science)

**Gateway** · **Wiki Home** · **Evaluation Science** · Known Limitations

## Abstract

Limitations that sit in the science rather than the implementation. They affect what a metric can or cannot tell us; fixing them is research, not engineering.

## Dataset limitations

- MEANTIME is small and news-domain-skewed; results may not generalize to narrative, technical, or conversational text.
- Gold annotations themselves contain disagreements, especially at the TLINK layer.

## Metric limitations

- No single coreference metric captures topology + mention detection correctly; triples must be reported.
- TLINK P/R/F depends on whether closure is applied before scoring; results are incomparable across studies that choose differently.
- "Accuracy" on event attributes assumes a closed vocabulary; open-vocabulary evaluations are more informative but harder to compare.

## Reasoning limitations

- LPG+contracts is less expressive than OWL-DL; some forms of inconsistency cannot be captured by contradiction pairs alone.
- Cross-document timeline alignment is a distinct research problem; within-document is a much weaker claim.

## Translating limitations into reports

- Every summary report includes a "Scope & Caveats" section that restates the applicable limitations.
- Error-mode counts are reported alongside metrics so a single number cannot hide a systemic failure.

## References

- [cybulska2014meantime]
- [uzzaman2013tempeval3]
- [tjong2003conll]

## See also

- [`what-quality-means.md`](what-quality-means.md)
- [`../55-evaluation-strategy/known-error-modes.md`](../55-evaluation-strategy/known-error-modes.md)
