<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# MEANTIME Bridge

**Gateway** · **Wiki Home** · **Evaluation Science** · MEANTIME Bridge

## Abstract

The MEANTIME bridge validator (milestone M8) compares the canonical structure produced by TextGraphX against the MEANTIME gold annotations, abstracted away from surface spans. It is the structural anchor that keeps the system honest over time.

## What it compares

- Canonical `Entity` chains vs gold entity chains.
- `TEvent` / `EventMention` structure vs gold event chains.
- `TIMEX` normalization vs gold temporal expressions.
- `EVENT_PARTICIPANT` edges vs gold participant role assignments.
- TLINK relation types (normalized to `temporal_reasoning_profile.canonical_reltypes`).

## How it works (high level)

1. Ingest the MEANTIME gold files once into a side graph.
2. Align documents by identifier.
3. For each document, walk canonical chains in both graphs and score structural alignment, not surface spans.
4. Emit a per-document and summary report under `src/textgraphx/datastore/evaluation/bridge/`.

Authoritative reference: [`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md).

## Why structural, not surface

- Different tokenizers produce different spans; penalizing the system for that confuses correctness with preprocessing choice.
- The reasoning contracts live at the canonical layer; alignment there is what downstream consumers care about.

## Limits

- English MEANTIME subset only.
- Gold attribute vocabularies do not perfectly match TextGraphX's controlled vocabularies; normalization rules are documented in the bridge report.

## References

- [cybulska2014meantime]
- [pustejovsky2003timeml]
- [hur2024unifying]

## See also

- [`what-quality-means.md`](what-quality-means.md)
- [`../55-evaluation-strategy/self-certifying-reports.md`](../55-evaluation-strategy/self-certifying-reports.md)
- [`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md)
