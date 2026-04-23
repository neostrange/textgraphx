<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Lexical Semantics (WordNet)

**Gateway** · **Wiki Home** · **Linguistics** · Lexical Semantics (WordNet)

## Abstract

TextGraphX enriches tokens and entities with WordNet lexnames (supersenses) to give the reasoning layer coarse lexical categories (e.g., `noun.event`, `noun.person`, `verb.communication`).

## What is represented

Properties on `TagOccurrence` / `Entity`:

- `wnLexname` — canonical supersense label.
- `wn_supersense` — alternate name retained for compatibility.
- `wnSynsetId` — synset identifier when disambiguated.
- `wnGloss` — optional gloss.

See the auto-generated property list in [`../40-ontology-and-schema/schema-autogen.md`](../40-ontology-and-schema/schema-autogen.md).

## Where it is produced

Inside the ingestion/refinement stages — see WordNet-related helpers under [`src/textgraphx/text_processing_components/`](../../../src/textgraphx/text_processing_components) and [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py).

## Why this matters

- Nominal event detection uses `noun.event` / `noun.act` / `noun.process` as one strong signal.
- Participant role validation can reject obviously-wrong categories (e.g., a `noun.location` as the AGENT of a communication verb).
- Typed retrieval (GraphRAG-style) benefits from supersense filters.

## Limits and pitfalls

- WordNet coverage is English-only and skewed toward general-domain vocabulary.
- Supersense assignment is a coarse proxy; precise sense disambiguation remains a research-grade open problem.

## References

- [miller1995wordnet]
- [fellbaum1998wordnet]

## See also

- [`named-entities-and-linking.md`](named-entities-and-linking.md)
- [`../30-algorithms/wsd-wordnet.md`](../30-algorithms/wsd-wordnet.md)
