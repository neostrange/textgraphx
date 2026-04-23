<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Coreference Formats

**Gateway** · **Wiki Home** · **Datasets** · Coreference Formats

## Abstract

Coreference annotations arrive in a handful of formats; TextGraphX normalizes all of them onto the same mention/antecedent structure.

## Formats in scope

- **CoNLL-2003** — named-entity + chunk + POS annotations; coreference is not part of CoNLL-2003 itself but ingestion is compatible.
- **CoNLL-2012 (OntoNotes).** Full coreference annotations with layered linguistic features.
- **NAF coref layer.** Used by MEANTIME; directly consumed by the ingestion reader.

## Normalization

- Every gold chain is reduced to a sequence of `CorefMention` + `Antecedent` nodes at evaluation time.
- Surface-level differences (mention-span conventions, singletons included/excluded) are recorded in the evaluator metadata so reports cannot silently drift.

## Limits

- Singleton handling varies across formats; metrics are reported twice (with and without singletons) when relevant.
- Nested mention conventions differ; the system prefers the outermost non-pronominal mention as the canonical surface.

## References

- [tjong2003conll]
- [jurafsky-martin-slp]

## See also

- [`../10-linguistics/coreference-and-discourse.md`](../10-linguistics/coreference-and-discourse.md)
- [`../30-algorithms/coref-resolution.md`](../30-algorithms/coref-resolution.md)
