<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Ontology Overview

**Gateway** · **Wiki Home** · **Ontology & Schema** · Overview

## Abstract

The TextGraphX ontology is expressed in three coordinated artifacts: [`ontology.json`](../../../src/textgraphx/schema/ontology.json) (machine-readable policy), [`../../schema.md`](../../schema.md) (human contract), and migrations under `src/textgraphx/schema/migrations/` (enforced change log). This page is the narrative map over all three.

## Three artifacts, one ontology

| Artifact | Role | Authority |
| --- | --- | --- |
| `ontology.json` | Machine-readable labels, relationships, contracts, and policies. | Used directly by phase assertions and diagnostics. |
| `docs/schema.md` | Human-readable contract with governance rules and precedence. | Canonical prose reference. |
| `schema/migrations/` | Cypher migrations that have been applied. | Enforced at the database layer. |

Precedence when they disagree (from [`../../schema.md`](../../schema.md)): runtime write paths → migrations → `schema.md` → `ontology.json` → architectural docs.

## What `ontology.json` declares

See the auto-generated tables in [`schema-autogen.md`](schema-autogen.md) for the current values.

Top-level sections:

- `nodes` (23 entries) — node label → purpose + key properties + id convention.
- `relationships` (30 entries) — relationship type → shape string (source → target, with optional properties).
- `schema_tiers` — `canonical` / `optional` / `legacy` label and relationship partitions.
- `governance_mode` — hard-contract vs advisory scope, legacy policy.
- `identity_policy` — document id type, ownership.
- `span_contract` — authoritative span fields and legacy aliases.
- `relation_endpoint_contract` — allowed endpoint types per relationship.
- `event_attribute_vocabulary` — closed vocabularies for event attributes (`tense`, `aspect`, `polarity`, `certainty`, `factuality`, etc.).
- `temporal_reasoning_profile` — Allen-algebra canonical relation types, contradiction pairs, closure rules, consistency policy, DCT anchor policy. See [`reasoning-contracts.md`](reasoning-contracts.md).
- `argument_type_vocabulary` — controlled SRL/participant type vocabulary.
- `dynamic_label_policy` — rules for dynamic labels on selected nodes (e.g., `NUMERIC`, `VALUE`).
- `deprecated_relationships` — legacy edges retained with a documented replacement.
- `migration_manifest` — applied migrations index.
- `diagnostics` — named diagnostic queries the system can run on the live graph.

## How it is used at runtime

- [`phase_assertions.py`](../../../src/textgraphx/phase_assertions.py) reads relevant contract sections to validate phase outputs.
- [`reasoning_contracts.py`](../../../src/textgraphx/reasoning_contracts.py) owns the Python-side contract surface.
- `diagnostics` entries back the query pack used in self-certifying reports.

## Schema tiers in practice

- **Canonical** — the tier downstream reasoning and evaluators should target.
- **Optional** — accepted but not required; consumers must tolerate absence.
- **Legacy** — preserved for compatibility; consumers should not write new data here and should prefer canonical replacements.

See the live breakdown in [`schema-autogen.md`](schema-autogen.md).

## Relationship to the origin paper

Schema tiering, endpoint contracts, the temporal reasoning profile, and the span coordinate contract are TextGraphX additions; the origin paper (Hur et al., 2024) did not formalize these. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## References

- [hur2024unifying]
- [hogan2021kg]
- [paulheim2017kg]

## See also

- [`schema-semantics.md`](schema-semantics.md)
- [`reasoning-contracts.md`](reasoning-contracts.md)
- [`span-coordinate-contract.md`](span-coordinate-contract.md)
- [`schema-autogen.md`](schema-autogen.md)
- [`../../schema.md`](../../schema.md)
