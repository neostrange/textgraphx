<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# For Symbolic AI

**Gateway** · **Wiki Home** · **Applications** · For Symbolic AI

## Abstract

TextGraphX produces a typed, contract-governed graph suitable as input to symbolic reasoners, rule engines, and knowledge-graph completion systems.

## Why this matters for symbolic systems

- Canonical typing (`relation_endpoint_contract`, `event_attribute_vocabulary`) lets a rule engine assume shape rather than probe it.
- Allen-algebra canonical TLINK types map cleanly to temporal-reasoning predicates in systems expecting qualitative temporal calculus.
- Explicit provenance makes retraction and belief revision straightforward.
- Canonical/legacy tiering ([`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md)) gives reasoners a principled way to ignore deprecated edges.

## Integration patterns

- **Forward-chaining over canonical TLINKs.** Use `closure_rules` declared in `temporal_reasoning_profile` as the starting rule set.
- **Event-calculus-style occurrence predicates.** Map `TEvent` to `happens(e, t)` where `t` is drawn from linked `TIMEX` anchors.
- **Consistency checking.** Enforce `contradiction_pairs` as integrity constraints.

## Limits

- LPG is not OWL-DL; some ontological commitments (disjoint classes, cardinality) are only partially expressible.
- Open-world assumptions apply; the absence of an edge is not evidence of falsehood.

## References

- [allen1983intervals]
- [owl-time-2022]
- [hogan2021kg]
- [paulheim2017kg]
- [cidoc-crm]

## See also

- [`for-llm-genai.md`](for-llm-genai.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
