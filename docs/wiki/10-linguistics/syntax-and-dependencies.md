<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Syntax and Dependencies

**Gateway** · **Wiki Home** · **Linguistics** · Syntax and Dependencies

## Abstract

Syntactic structure (POS, lemma, dependency relations) is the bottom layer of the LPG. It gives every downstream phase span coordinates, lemma-typed grouping, and head-dependent relations to walk over.

## What is represented

- **`TagOccurrence`** — one tokenizer output. Carries `doc_id`, `sent_idx`, `token_idx`, surface form, POS, lemma, `start_char`/`end_char`, `start_tok`/`end_tok`.
- **`Tag`** — lemma-level grouping. Multiple `TagOccurrence` nodes with the same lemma share a `Tag`.
- **`Sentence`** — the sentence container. Owns its tokens via `HAS_TOKEN`.
- **`AnnotatedText`** — the document container.
- **`IS_DEPENDENT`** — typed dependency edge between `TagOccurrence` nodes. Property `type` carries the dependency label (e.g., `nsubj`, `dobj`, `amod`, ...).
- **`HAS_NEXT`** — linear-order chain over tokens for stable iteration.

## Where it is produced

[`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py) and [`src/textgraphx/text_processing_components/`](../../../src/textgraphx/text_processing_components) (spaCy + NLTK backends).

## Why TextGraphX keeps it explicit

- Event detection and participant resolution walk dependency paths (subject/object/obl) rather than re-parsing text.
- Token IDs are the anchor for every mention node's span contract ([`../40-ontology-and-schema/span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md)).
- Sentence scoping is required for coreference windows, event-coreference candidate generation, and TLINK locality rules.

## Limits and pitfalls

- Dependency labels depend on the upstream parser; label-set drift across parser versions is a real risk (pinned versions in the environment mitigate this).
- Multi-word expressions are not merged into a single token; downstream stages handle multi-token spans at the mention layer.

## References

- [jurafsky-martin-slp]
- [tjong2003conll]

## See also

- [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)
- [`named-entities-and-linking.md`](named-entities-and-linking.md)
- [`semantic-role-labeling.md`](semantic-role-labeling.md)
