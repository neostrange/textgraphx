<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — Coreference Resolution

**Gateway** · **Wiki Home** · **Algorithms** · Coreference Resolution

## Purpose

Resolve mentions that refer to the same discourse entity into coreference chains.

## Inputs

- `TagOccurrence` sequence, POS, dependencies.
- `NamedEntity` / `EntityMention` spans (when available) used as chain seeds.

## Outputs

- `CorefMention` nodes for each mention participating in a chain.
- `Antecedent` nodes as chain heads.
- `COREF` edges and `IN_MENTION` edges from tokens.

## Assumptions

- Mention detection is done before or jointly with linking; orphan mentions are tolerated.
- Coreference is document-scoped by default.

## Limits / failure modes

- Long-range pronominal resolution is brittle.
- Cataphora and split antecedents are not specially handled.
- Event coreference is a separate problem, handled at the `EventMention → TEvent` canonicalization.

## Implementation

- [`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py) (coref integration).
- [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py) (canonical fusion).

## Evaluation

- Coref-aware entity evaluator under `src/textgraphx/evaluators/`.
- MEANTIME bridge compares chain structure, not surface mentions.

## References

- [jurafsky-martin-slp]
- [tjong2003conll]

## See also

- [`../10-linguistics/coreference-and-discourse.md`](../10-linguistics/coreference-and-discourse.md)
- [`entity-fusion-and-canonicalization.md`](entity-fusion-and-canonicalization.md)
