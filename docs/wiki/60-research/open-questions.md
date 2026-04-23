<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Open Questions

**Gateway** · **Wiki Home** · **Research** · Open Questions

## Abstract

The unresolved research problems the system is designed to attack — or could be extended to.

## Structural / schema

- What is the right expressivity sweet spot between LPG and OWL-DL for event-centric temporal KGs?
- How many schema tiers are enough before governance becomes its own maintenance burden?

## Temporal reasoning

- What is the best conservative closure policy that preserves information without inflating contradiction counts?
- How should cross-document temporal alignment be modeled — one anchor per corpus, per topic, or per entity?
- How should modality (hypotheticals, conditionals, counterfactuals) be represented in the TLINK graph?

## Event coreference

- What mention-to-canonical signals dominate in noisy corpora?
- How should event coreference interact with entity coreference when evidence conflicts?

## Evaluation science

- Are the current metrics sufficient, or do we need composite metrics that combine correctness with consistency?
- How do we make regression gates tolerant of intentional schema evolution without masking real regressions?

## Relation to the origin paper

These questions extend well beyond the scope of Hur et al. (2024). The origin paper framed five task tracks; the open questions above concern the governance, reasoning, and evaluation layers built on top. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## References

- [hur2024unifying]
- [allen1983intervals]
- [hogan2021kg]

## See also

- [`hypotheses-and-experiments.md`](hypotheses-and-experiments.md)
- [`related-work.md`](related-work.md)
- [`paper-vs-current.md`](paper-vs-current.md)
