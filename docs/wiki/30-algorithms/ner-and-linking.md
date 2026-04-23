<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — NER and Linking

**Gateway** · **Wiki Home** · **Algorithms** · NER and Linking

## Purpose

Identify named-entity mentions in text and promote them to canonical `Entity` nodes with type labels.

## Inputs

- `TagOccurrence` sequence for each sentence (from ingestion).
- Dependency labels (optional; used to widen mention spans to nominal heads).

## Outputs

- `NamedEntity` mention nodes (span + NE type).
- `EntityMention` where the mention is nominal but not a proper name.
- `Entity` canonical nodes with `REFERS_TO` edges from their mentions.

## Assumptions

- Upstream tokenizer and POS tagger are pinned and deterministic.
- NE type inventory aligns with the system's normalization map (PERSON, LOC, ORG, DATE, MISC, NUMERIC, VALUE — see `ontology.json` dynamic-label policy).

## Limits / failure modes

- Long-range co-reference is handled in a separate stage (see [`coref-resolution.md`](coref-resolution.md)); NER alone does not deduplicate.
- Rare entity types (legal instruments, biomedical entities) require corpus-specific models.

## Implementation

- [`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py) (NER stage).
- [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py) (canonical fusion).

## Evaluation

- `src/textgraphx/evaluators/` (entity evaluator — see [`../55-evaluation-strategy/README.md`](../55-evaluation-strategy/README.md)).
- MEANTIME bridge validator checks structural alignment of entity participants.

## References

- [tjong2003conll]
- [fillmore2006framenet]

## See also

- [`../10-linguistics/named-entities-and-linking.md`](../10-linguistics/named-entities-and-linking.md)
- [`entity-fusion-and-canonicalization.md`](entity-fusion-and-canonicalization.md)
