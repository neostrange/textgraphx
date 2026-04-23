<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — Word Sense Disambiguation (WordNet)

**Gateway** · **Wiki Home** · **Algorithms** · WSD / WordNet

## Purpose

Enrich tokens and canonical entities with WordNet supersenses (lexnames) and, where confident, synset identifiers.

## Inputs

- `TagOccurrence` with POS + lemma.
- Surrounding context within the sentence.

## Outputs

- Properties on `TagOccurrence` / `Entity`: `wnLexname`, `wn_supersense`, `wnSynsetId`, `wnGloss` (optional).

## Assumptions

- English text; WordNet 3.x.
- Supersense is a sufficient proxy when full WSD confidence is low; the system prefers supersense over a low-confidence synset assignment.

## Limits / failure modes

- Domain-specific senses (biomedical, legal) are poorly covered.
- Metaphoric or figurative uses typically snap to the most frequent sense.

## Implementation

- WordNet helpers inside [`src/textgraphx/text_processing_components/`](../../../src/textgraphx/text_processing_components) and enrichment in [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py).

## Evaluation

- `evaluate_wordnet_nominals.py` at the repo root is the reference script used for nominal-event signal validation.
- Downstream signal quality is also visible in nominal-event detection metrics.

## References

- [miller1995wordnet]
- [fellbaum1998wordnet]

## See also

- [`../10-linguistics/lexical-semantics-wordnet.md`](../10-linguistics/lexical-semantics-wordnet.md)
