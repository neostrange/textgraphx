<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Glossary

**Gateway** · **Wiki Home** · **Foundations** · Glossary

Short, authoritative definitions reused across the wiki. For deeper treatment follow the cross-links.

## Core graph concepts

- **LPG (Labeled Property Graph)** — the Neo4j-native model: typed nodes and directed typed edges, both carrying properties.
- **Node label** — e.g. `TagOccurrence`, `Entity`, `TEvent`. See [`schema-autogen.md`](../40-ontology-and-schema/schema-autogen.md).
- **Relationship type** — e.g. `REFERS_TO`, `TLINK`, `EVENT_PARTICIPANT`.
- **Canonical node** — identity-bearing node (`Entity`, `TEvent`, `TIMEX`). Downstream reasoning joins here.
- **Mention node** — evidence node for a span of text (`EntityMention`, `EventMention`, `TimexMention`). Always points at its canonical via `REFERS_TO`.
- **Span contract** — the invariants on `start_tok`/`end_tok`/`start_char`/`end_char`. See [`span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md).

## Linguistic concepts

- **Token (`TagOccurrence`)** — a single tokenizer output, unique per `<doc>_<sent>_<token_idx>`.
- **Lemma / Tag** — type-level grouping for tokens sharing a lemma.
- **Dependency** — syntactic relation between two `TagOccurrence` nodes (`IS_DEPENDENT`).
- **NER mention (`NamedEntity`)** — surface-level named-entity span.
- **Coreference chain** — `CorefMention --COREF--> Antecedent`.
- **SRL frame** — predicate-argument structure (`Frame`, `FrameArgument`).
- **WordNet lexname / supersense** — coarse lexical category attached to tokens / entities (`wnLexname`, `wn_supersense`).

## Temporal concepts

- **TIMEX** — canonical time expression (ISO-TimeML).
- **TEvent** — canonical event.
- **EventMention** — event evidence span linked to its canonical `TEvent`.
- **Signal** — temporal connective (before, after, while, ...) realized as a `Signal` node.
- **TLINK** — typed temporal relation between `TEvent`/`TIMEX` endpoints.
- **Allen's interval algebra** — the 13 qualitative relations used as the canonical relation-type inventory.
- **DCT (Document Creation Time)** — the per-document reference anchor for unresolved deictic expressions.

## Governance concepts

- **Schema tier** — `canonical` / `optional` / `legacy`, declared in [`ontology.json`](../../../src/textgraphx/schema/ontology.json).
- **Reasoning contract** — machine-readable constraint on endpoints, attributes, or temporal consistency.
- **Phase assertion** — runtime predicate a phase must satisfy before it is allowed to advance.
- **Bridge validator (M8)** — MEANTIME-vs-system structural comparison.
- **Quality gate** — CI-enforced regression check against a baseline snapshot.

## See also

- [`theme-and-rationale.md`](theme-and-rationale.md)
- [`concept-map.md`](concept-map.md)
- [`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md)
