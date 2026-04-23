<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — Entity Fusion and Canonicalization

**Gateway** · **Wiki Home** · **Algorithms** · Entity Fusion & Canonicalization

## Purpose

Promote mention-level evidence (`NamedEntity`, `EntityMention`, `CorefMention`, chain heads) into canonical `Entity` nodes with deterministic IDs.

## Inputs

- Mention-layer nodes emitted by ingestion.
- Coreference chains.
- Optional external identifiers (when enabled in pipeline config).

## Outputs

- Canonical `Entity` nodes with `doc_id`, type, surface forms, and — when applicable — `NUMERIC` / `VALUE` dynamic labels.
- `REFERS_TO` edges from every mention into exactly one canonical entity.

## Assumptions

- Within-document fusion is deterministic; cross-document fusion is opt-in and typically confined to MEANTIME-bridge workflows.
- Participant roles depend on canonical identity, so fusion must precede event-participant linking.

## Limits / failure modes

- Abbreviations and nicknames are a frequent source of over-merging.
- Identical surface forms that denote different real-world entities within one document (e.g., two people named "Smith") require contextual disambiguation that a generic fuser does not always get right.

## Implementation

- [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py).

## Evaluation

- Entity evaluator under `src/textgraphx/evaluators/`.
- MEANTIME bridge: structural alignment against gold entity chains.

## References

- [hur2024unifying]
- [tjong2003conll]

## See also

- [`ner-and-linking.md`](ner-and-linking.md)
- [`coref-resolution.md`](coref-resolution.md)
- [`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md)
