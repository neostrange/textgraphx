<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Reasoning Contracts

**Gateway** · **Wiki Home** · **Ontology & Schema** · Reasoning Contracts

## Abstract

TextGraphX exposes three machine-readable reasoning contracts in [`ontology.json`](../../../src/textgraphx/schema/ontology.json): the relation endpoint contract, the event attribute vocabulary, and the temporal reasoning profile. Together they let consumers reason over the graph with declared guarantees rather than folklore.

## 1. Relation endpoint contract

Declared under `relation_endpoint_contract`. For each relationship that carries a typing constraint, the contract names the allowed endpoint labels and any required properties.

Example entries (see [`schema-autogen.md`](schema-autogen.md) for the live list):

- `REFERS_TO` — mention label → canonical label (with per-kind pairings).
- `EVENT_PARTICIPANT` — `Entity` / `NUMERIC` / `FrameArgument` / `VALUE` → `TEvent` / `EventMention`.
- `FRAME_DESCRIBES_EVENT` — `Frame` → `TEvent`.
- `INSTANTIATES` — `Frame` → `EventMention`.
- `HAS_FRAME_ARGUMENT` — `FrameArgument` → `Frame`.
- `TRIGGERS` — `TagOccurrence` → `TimexMention` / `TEvent` / `Signal`.

Enforcement point: [`phase_assertions.py`](../../../src/textgraphx/phase_assertions.py) and [`reasoning_contracts.py`](../../../src/textgraphx/reasoning_contracts.py).

## 2. Event attribute vocabulary

Declared under `event_attribute_vocabulary`. Closed vocabularies for attributes set on `TEvent` / `EventMention`:

- `tense` (e.g., `PAST`, `PRESENT`, `FUTURE`, `NONE`).
- `aspect` (e.g., `PERFECTIVE`, `IMPERFECTIVE`, ...).
- `polarity`.
- `certainty`.
- `factuality`.
- plus additional per-attribute entries as declared.

Rule: any value written outside the declared vocabulary is a contract violation and will surface in diagnostics.

## 3. Temporal reasoning profile

Declared under `temporal_reasoning_profile`. This is the substrate for temporal reasoning.

Components:

- **`canonical_reltypes`** — the canonical TLINK relation-type inventory. Allen-algebra aligned (e.g., `BEFORE`, `AFTER`, `INCLUDES`, `IS_INCLUDED`, `DURING`, `SIMULTANEOUS`, `IAFTER`, `IBEFORE`, `BEGINS`, `ENDS`, `BEGUN_BY`, `ENDED_BY`, `OVERLAPS` — see [`schema-autogen.md`](schema-autogen.md) for the live list).
- **`contradiction_pairs`** — pairs of relation types that cannot both hold for the same endpoint pair. A graph with both is inconsistent.
- **`closure_rules`** — conservative transitive inferences allowed under the consistency policy.
- **`consistency_policy`** — how aggressively the system closes and rejects inconsistencies.
- **`dct_anchor_policy`** — how document creation time is used as the default anchor for unresolved deictic expressions.

Usage:

- TLINK evaluators use `canonical_reltypes` to normalize system and gold labels onto a common inventory before scoring.
- Consistency scoring flags any `contradiction_pair` co-occurrence.
- Closure is applied conservatively: inferred edges are marked as such; only rules in `closure_rules` are applied.

## Why contracts, not narrative prose

- Contracts are mechanically checkable. Narrative documentation drifts.
- Contracts are consumable by external tools (e.g., an LLM validator, a reasoner, a downstream KG embedding pipeline).
- Contracts make extensions auditable: a change to a contract is a code change with a reviewable diff.

## Relationship to the origin paper

The origin paper (Hur et al., 2024) did not expose reasoning contracts; TLINK extraction was evaluated but not bounded by a declared consistency/closure policy. The three contracts above are TextGraphX additions. See [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## References

- [hur2024unifying]
- [allen1983intervals]
- [pustejovsky2003timeml]
- [iso24617-1-2012]

## See also

- [`ontology-overview.md`](ontology-overview.md)
- [`schema-semantics.md`](schema-semantics.md)
- [`schema-autogen.md`](schema-autogen.md)
- [`span-coordinate-contract.md`](span-coordinate-contract.md)
