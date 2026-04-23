<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# WordNet / Synsets

**Gateway** · **Wiki Home** · **Datasets** · WordNet

## Abstract

WordNet provides the lexical-semantic backbone used by TextGraphX for coarse sense enrichment (supersenses / lexnames) and selective synset tagging.

## What it provides

- Synsets with glosses.
- Lexnames (supersenses) such as `noun.event`, `noun.person`, `verb.communication`, ...
- Hypernymy/hyponymy relations useful for type-based filtering.

## How TextGraphX uses it

- Token-level enrichment: `wnLexname`, `wn_supersense`, `wnSynsetId`, `wnGloss`.
- Nominal event detection uses `noun.event` / `noun.act` / `noun.process` as a strong positive signal.
- Typed GraphRAG retrieval can filter by supersense category.

## Limits

- Coverage is English-only.
- Sense inventories skew toward general vocabulary; domain terms (biomedical, legal) are weak.

## References

- [miller1995wordnet]
- [fellbaum1998wordnet]

## See also

- [`../10-linguistics/lexical-semantics-wordnet.md`](../10-linguistics/lexical-semantics-wordnet.md)
- [`../30-algorithms/wsd-wordnet.md`](../30-algorithms/wsd-wordnet.md)
