<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Integration Patterns

**Gateway** · **Wiki Home** · **Applications** · Integration Patterns

## Abstract

Common ways to plug TextGraphX into a wider system. Each pattern names its inputs, outputs, and the contracts a consumer should rely on.

## Pattern 1 — Ingestion pipeline (batch)

- **Input.** Raw text / NAF / MEANTIME XML.
- **Output.** Typed subgraph in the target Neo4j instance.
- **Contracts consumer relies on.** Canonical chains, span contract, relation endpoint contract, event attribute vocabulary.

## Pattern 2 — Read-side GraphRAG

- **Input.** Query (natural-language or structured).
- **Output.** Retrieved subgraph + source spans.
- **Contracts consumer relies on.** Canonical chains so entities/events deduplicate; TLINK canonical reltypes so temporal neighbors are uniformly typed.

## Pattern 3 — Quality audit for a third-party extractor

- **Input.** A third-party KG produced by another tool.
- **Output.** Diagnostics from `ontology.json.diagnostics` + contract-violation counts.
- **Contracts consumer relies on.** `relation_endpoint_contract`, `temporal_reasoning_profile.contradiction_pairs`.

## Pattern 4 — Timeline service

- **Input.** Entity id / topic.
- **Output.** Chronologically ordered sequence of `TEvent`s with participants and links to source spans.
- **Contracts consumer relies on.** Canonical TLINK reltypes, `event_attribute_vocabulary`, span contract.

## Pattern 5 — Evaluation sandbox

- **Input.** A new pipeline variant.
- **Output.** Self-certifying report + regression gate outcome.
- **Contracts consumer relies on.** The same schema/contracts used by the baseline; no silent baseline updates.

## Anti-patterns (avoid)

- Writing to the graph without going through a phase with its assertions.
- Bypassing canonical chains by querying mention nodes directly for identity-bearing reasoning.
- Ignoring TLINK contradictions because "they are few".

## See also

- [`use-cases.md`](use-cases.md)
- [`../55-evaluation-strategy/strategy-overview.md`](../55-evaluation-strategy/strategy-overview.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
