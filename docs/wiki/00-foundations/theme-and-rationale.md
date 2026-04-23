<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Theme and Rationale

**Gateway** · **Wiki Home** · **Foundations** · Theme and Rationale

## Abstract

TextGraphX turns unstructured text into an event-centric, temporally-anchored knowledge graph that is explainable, queryable, and testable. Its design principle is that **unified context** — tokens, mentions, entities, events, participants, and time — belongs in a single labeled property graph (LPG) so downstream reasoning is structural rather than re-parsed from text.

## Why this matters to TextGraphX

Every design choice in the system follows from three commitments:

1. **Span-grounded truth.** Every extracted element retains token and character coordinates so answers can be traced back to source text. See [`span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md).
2. **Canonical vs mention separation.** Mentions are evidence; canonical entities and events are the reasoning substrate. This duality is enforced by hard referential contracts ([`schema.md`](../../schema.md), §Governance).
3. **Temporal reasoning as a first-class concern.** The graph encodes events, time expressions, signals, and temporal links in a form compatible with Allen's interval algebra ([`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)).

## Key concepts

- **Labeled Property Graph (LPG)** — the Neo4j-native model used end-to-end.
- **Pipeline of phases** — ingestion → refinement → temporal → event enrichment → TLINK (see [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)).
- **Reasoning contracts** — machine-readable invariants in [`ontology.json`](../../../src/textgraphx/schema/ontology.json) that any consumer can rely on.
- **Self-certifying evaluation** — phase assertions, MEANTIME bridge, and quality gates turn "did it work?" into a deterministic CI answer ([`../55-evaluation-strategy/README.md`](../55-evaluation-strategy/README.md)).

## How TextGraphX realizes the theme

| Theme | Realization |
| --- | --- |
| Unified context | LPG schema with 23 node labels / 30 relationship types ([`schema-autogen.md`](../40-ontology-and-schema/schema-autogen.md)). |
| Span-grounded | `start_tok`/`end_tok`/`start_char`/`end_char` on every mention node. |
| Mention vs canonical | `EntityMention --REFERS_TO--> Entity`, `EventMention --REFERS_TO--> TEvent`, etc. |
| Temporal reasoning | `temporal_reasoning_profile` in `ontology.json`; Allen-algebra canonical relation types; contradiction pairs; conservative closure. |
| Reproducibility | Deterministic IDs, provenance/authority policy ([`../../PROVENANCE_AUTHORITY_POLICY.md`](../../PROVENANCE_AUTHORITY_POLICY.md)). |
| Regression safety | Baseline snapshots under `src/textgraphx/datastore/evaluation/baseline/` + `tools/check_quality_gate.py`. |

## Relation to the origin paper

The project originated from Hur, Janjua & Ahmed (2024) — see [`origin-paper.md`](origin-paper.md). The paper established the pipeline-LPG paradigm and the five task tracks. The current system treats that proposal as **origin and motivation**, not as a specification, and extends it substantially along schema, contracts, reasoning, evaluation, and governance axes.

## Limitations and risks

- LPG does not have the formal expressivity of OWL-DL; reasoning stays at the "contract + rule" level.
- The pipeline is sequential by design (stage outputs feed the next); parallelism happens inside stages, not across them.
- Temporal reasoning is document-scoped by default; cross-document temporal alignment requires explicit anchoring.

## References

- [hur2024unifying]
- [hogan2021kg]
- [allen1983intervals]
- [robinson2015graph]

## See also

- [`research-objectives.md`](research-objectives.md)
- [`glossary.md`](glossary.md)
- [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)
