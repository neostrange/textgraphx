<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Span Coordinate Contract

**Gateway** · **Wiki Home** · **Ontology & Schema** · Span Coordinate Contract

## Abstract

Every span-bearing mention node carries explicit token and character coordinates, scoped to its document. This contract is what makes extractions traceable, evaluable, and MEANTIME-bridgeable.

## Authoritative fields

Declared under `span_contract` in [`ontology.json`](../../../src/textgraphx/schema/ontology.json):

- **Token fields.** `start_tok`, `end_tok` (0-indexed, half-open is **not** used — see below).
- **Character fields.** `start_char`, `end_char`.
- **Legacy aliases.** Older labels (`index`, `end_index`, `startIndex`, `endIndex`) are accepted for backward compatibility. New code must write the canonical fields.

The live list of aliases is in [`schema-autogen.md`](schema-autogen.md).

## Invariants (hard contract)

For every span-bearing mention node (`NamedEntity`, `EntityMention`, `EventMention`, `TimexMention`, `Signal`, `Frame`, `FrameArgument`, `CorefMention`, `Antecedent`, `NounChunk`):

1. `start_tok` and `end_tok` are present and integer-typed.
2. `start_tok <= end_tok`.
3. When both token and character fields are present, they are internally consistent (same span).
4. `doc_id` is present on mention nodes that require document scoping (hard scope defined in `identity_policy`).

Violations are caught by phase assertions and surfaced as hard failures.

## Document scoping

Spans are always document-scoped. A span with identical coordinates in a different document is a different span. This matters for:

- MEANTIME bridge alignment ([`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md)).
- Cross-document event coreference (which must compare canonical events, not spans).
- TLINK consistency checking within a document.

## Head tokens and heads

Mention nodes that declare a syntactic head also set:

- `head` — head token text.
- `headTokenIndex` — doc-scoped token index of the head.

These are required for event participant resolution and for head-anchored UID computation in the MEANTIME bridge.

## Legacy aliases and migration

- Legacy aliases are preserved; new writes must prefer the canonical names.
- Evaluator code reads both canonical and alias fields to remain compatible with older data.
- A dedicated migration (recorded in `migration_manifest`) is required before an alias can be retired.

## Relationship to the origin paper

The origin paper used span indices implicitly, without a declared contract or coordinate discipline. TextGraphX promotes spans to a first-class, enforceable invariant. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## References

- [hur2024unifying]
- [cybulska2014meantime]

## See also

- [`schema-semantics.md`](schema-semantics.md)
- [`ontology-overview.md`](ontology-overview.md)
- [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)
