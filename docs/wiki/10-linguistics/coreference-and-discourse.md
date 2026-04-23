<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Coreference and Discourse

**Gateway** · **Wiki Home** · **Linguistics** · Coreference and Discourse

## Abstract

Coreference chains tie multiple mentions to the same discourse referent. TextGraphX keeps them explicit as a mention-layer structure that feeds canonicalization in the refinement phase.

## What is represented

- **`CorefMention`** — a mention participating in a coreference chain.
- **`Antecedent`** — the chain head (or previous antecedent).
- **`COREF`** — `CorefMention` → `Antecedent`.
- **`IN_MENTION`** — `TagOccurrence` → `CorefMention` (linking the tokens that constitute the mention).
- **`REFERS_TO`** — used to link mention-level evidence to the canonical `Entity` once refinement has resolved identity.

## Where it is produced

Coreference resolution runs inside ingestion (see [`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py)); canonical `Entity` fusion happens in [`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py).

## Why this matters

- Event participant detection benefits from chain resolution — *"he"* linked to *"Alice"* becomes a legitimate AGENT candidate.
- Timeline construction needs discourse-level identity so mentions across sentences can share a canonical subject.

## Limits and pitfalls

- Pronominal reference across long stretches of discourse is noisy; chain errors compound into participant errors.
- Event coreference is a distinct problem from entity coreference; the former is handled at the `EventMention` → `TEvent` canonicalization layer.

## References

- [jurafsky-martin-slp]
- [tjong2003conll]

## See also

- [`../30-algorithms/coref-resolution.md`](../30-algorithms/coref-resolution.md)
- [`named-entities-and-linking.md`](named-entities-and-linking.md)
- [`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md)
