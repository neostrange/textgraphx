<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Schema Semantics — Canonical / Optional / Legacy

**Gateway** · **Wiki Home** · **Ontology & Schema** · Schema Semantics

## Abstract

The schema is explicitly tiered so consumers can rely on canonical shapes while legacy compatibility is preserved during migrations. This page explains the three tiers and the governance contract that holds them together.

## Canonical source of truth

The authoritative text for the contract lives in [`../../schema.md`](../../schema.md). This page is the wiki-side narrative; the machine-readable declaration is in [`ontology.json`](../../../src/textgraphx/schema/ontology.json); the live tables are in [`schema-autogen.md`](schema-autogen.md).

## The three tiers

### Canonical

**Definition.** The labels and relationships all new code must target. Downstream reasoning (TLINK consistency, event coreference, timeline construction) assumes only canonical shapes.

Typical canonical nodes (see live list in [`schema-autogen.md`](schema-autogen.md)):
`AnnotatedText`, `Sentence`, `TagOccurrence`, `NamedEntity`, `Entity`, `EntityMention`, `Frame`, `FrameArgument`, `TIMEX`, `TimexMention`, `TEvent`, `EventMention`, `Signal`.

Typical canonical relationships:
`REFERS_TO`, `EVENT_PARTICIPANT`, `FRAME_DESCRIBES_EVENT`, `INSTANTIATES`, `HAS_FRAME_ARGUMENT`, `TRIGGERS`, `TLINK`, `HAS_TOKEN`, `HAS_NEXT`, `IS_DEPENDENT`, `COREF`, `IN_MENTION`, `IN_FRAME`.

### Optional

**Definition.** Enrichment layers consumers may use if present but must not require. Absence is never a failure.

Examples: advanced enrichment properties under `semantic_enrichment_properties`, optional provenance fields on inferred edges, optional confidence scores.

### Legacy

**Definition.** Preserved edges/labels with a documented replacement. Not written by new code; queries should prefer the canonical alternative. Examples appear in `deprecated_relationships` (e.g., `DESCRIBES` → `FRAME_DESCRIBES_EVENT`, `PARTICIPATES_IN` → `EVENT_PARTICIPANT`, `PARTICIPANT` → `HAS_FRAME_ARGUMENT`/`EVENT_PARTICIPANT`).

## Governance rules (summary)

Pulled from [`../../schema.md`](../../schema.md) → Governance Mode (Balanced):

- **Hard-contract scope (must pass).** Identity keys, referential integrity of canonical chains, required core fields on canonical labels, span integrity (`start_tok <= end_tok`).
- **Advisory-contract scope (warn only).** Enrichment completeness, optional provenance, transitional dual-edge usage ratios.
- **Legacy policy.** Legacy labels/relationships survive until explicitly migrated.

Phase assertions and diagnostics enforce hard-contract scope at runtime; advisory violations appear as diagnostics only.

## Canonical chains to remember

These referential chains are hard contracts. A break in any of them is a hard failure:

```
NamedEntity / EntityMention --REFERS_TO--> Entity
TimexMention               --REFERS_TO--> TIMEX
EventMention               --REFERS_TO--> TEvent
Frame                      --INSTANTIATES--> EventMention
```

## Evolving the schema

- New labels/relationships enter as `canonical` only after an applied migration and a code write path.
- Deprecations move through `canonical → legacy → removal`, with the transition declared in `deprecated_relationships` and a replacement documented.
- See [`../../schema-evolution-plan.md`](../../schema-evolution-plan.md) for the procedural playbook.

## Relationship to the origin paper

The paper did not formalize tiering, canonical chains, or legacy policy; those are TextGraphX additions introduced to make the schema safely evolvable under CI. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## References

- [hur2024unifying]
- [hogan2021kg]

## See also

- [`ontology-overview.md`](ontology-overview.md)
- [`reasoning-contracts.md`](reasoning-contracts.md)
- [`schema-autogen.md`](schema-autogen.md)
- [`../../schema.md`](../../schema.md)
- [`../../schema-evolution-plan.md`](../../schema-evolution-plan.md)
