# Provenance & Authority Policy

This document defines how textgraphx resolves competing evidence from multiple
extractors while preserving additive graph evidence.

## Goals

1. Keep authoritative sources dominant for core semantics.
2. Preserve conflicting evidence instead of silently deleting it.
3. Make all inferred links auditable via provenance fields.

## Required Relationship Provenance Fields

All inferred relationships must carry:

- `confidence` in [0.0, 1.0]
- `evidence_source` (normalized lowercase source id)
- `rule_id` (phase/rule identifier)
- `authority_tier` (`primary` | `secondary` | `support`)
- `source_kind` (`service` | `rule` | `model` | `manual`)
- `conflict_policy` (`additive` | `merge` | `overwrite`)

Phase wrappers for temporal, event enrichment, and tlinks stamp these fields and
run provenance contract checks through `PhaseAssertions`.

## Authority Tiers

Default source-to-tier mapping lives in `authority.py`.

- `primary`: AllenNLP SRL, Temporal service outputs (TTK/HeidelTime), external coref
- `secondary`: event/tlink/refinement derived graph logic
- `support`: spaCy support features, DBpedia support signals, generic heuristics

## Conflict Resolution

`authority.decide_conflict(...)` defines deterministic conflict behavior.

Priority order:

1. Higher `authority_tier`
2. Higher `confidence`
3. Deterministic lexical tie-break

Policies:

- `additive`: keep both values, expose preferred winner.
- `merge`: keep both values, expose preferred winner (alias of additive for now).
- `overwrite`: replace only when incoming evidence outranks existing.

## Phase-Level Enforcement

When `enforce_provenance_contracts=True` in `PhaseAssertions`, the following are
checked for missing required provenance fields:

- `after_temporal`: `TLINK`
- `after_event_enrichment`: `DESCRIBES`, `FRAME_DESCRIBES_EVENT`, `PARTICIPANT`, `EVENT_PARTICIPANT`
- `after_tlinks`: `TLINK`

## Implementation Notes

- Wrappers stamp inferred links before running assertions.
- Wrappers use explicit `source_kind` and `conflict_policy` values.
- Validation helper: `validate_inferred_relationship_provenance(graph, rel_type)`.
