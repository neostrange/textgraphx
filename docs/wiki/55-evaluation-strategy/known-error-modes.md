<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Known Error Modes

**Gateway** · **Wiki Home** · **Evaluation Strategy** · Known Error Modes

## Abstract

An honest catalogue of systematic failure modes observed in evaluation. Keeping these visible prevents "surprise regressions" and guides where reviewer attention should focus.

## Linguistic layer

- **Dependency-label drift** when upstream parser versions change.
- **Nominal predicate under-coverage** for SRL.
- **Long-range pronominal coref** — chain errors propagate into participants.

## Temporal layer

- **Unresolved deictic TIMEX** when DCT is missing or ambiguous.
- **Narrative time-shifts** (flashbacks, conditionals) produce weak or absent TLINKs.
- **Closure inflation** if a permissive closure policy is applied.

## Event layer

- **Trigger over-generation** for light verbs (*have*, *take*, *make*).
- **Participant mis-typing** when NER type confidence is low.
- **Event/entity conflation** when a mention could be either.

## Graph / schema layer

- **Alias drift** between legacy span fields and canonical span fields.
- **Dangling mentions** — a `NamedEntity` without a `REFERS_TO` edge (hard-contract violation).
- **Contradiction pairs** — two canonical TLINK types asserted on the same endpoint pair.

## What to do about them

- Each error mode has a diagnostic query in `ontology.json.diagnostics`.
- Self-certifying reports include a dedicated section that counts occurrences per mode.
- Threshold-based regression gates fail when an error mode's count increases beyond baseline.

## See also

- [`strategy-overview.md`](strategy-overview.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
- [`../50-evaluation-science/known-limitations.md`](../50-evaluation-science/known-limitations.md)
