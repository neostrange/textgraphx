<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# For Event-Centric Temporal KGs

**Gateway** · **Wiki Home** · **Applications** · Event-Centric Temporal KGs

## Abstract

TextGraphX can be used as a building block for larger event-centric temporal knowledge graphs — either as the ingestion front-end, the normalization layer, or the structural audit surface.

## As an ingestion front-end

- Text → typed graph, ready to merge into a larger KG.
- Canonical/mention duality preserves evidence for merges.
- Span and document scoping keep provenance intact.

## As a normalization layer

- Existing KGs with ad-hoc temporal edges can be normalized onto `temporal_reasoning_profile.canonical_reltypes`.
- `contradiction_pairs` and `closure_rules` provide a quick audit of temporal soundness before downstream reasoning.

## As a structural audit surface

- `relation_endpoint_contract` catches typing errors missed by schema-only validation.
- Diagnostic queries (`ontology.json.diagnostics`) surface chain breaks, orphan mentions, and missing participants.
- Regression gates convert "the KG got worse" into a CI-enforced answer.

## Limits

- TextGraphX is document-scoped by default; cross-document KG construction requires an explicit canonicalization step outside this repo.
- Multi-lingual extension is research work, not a configuration flag.

## References

- [hogan2021kg]
- [paulheim2017kg]
- [cidoc-crm]
- [hur2024unifying]

## See also

- [`for-symbolic-ai.md`](for-symbolic-ai.md)
- [`for-context-engineering.md`](for-context-engineering.md)
- [`use-cases.md`](use-cases.md)
