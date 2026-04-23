<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Gold vs System Alignment

**Gateway** · **Wiki Home** · **Datasets** · Gold vs System Alignment

## Abstract

Before any metric can be computed, gold annotations must be aligned with system output. The alignment rules are explicit and the same set is used across every evaluator.

## Alignment rules

1. **Document identity.** Documents are aligned by `doc_id` (gold and system must agree on this field; see `identity_policy` in [`ontology.json`](../../../src/textgraphx/schema/ontology.json)).
2. **Mention alignment.** Default is exact span. Relaxed alignment (head-inclusive) is also reported for NER and event triggers.
3. **Canonical chain alignment.** Gold chains are matched to system chains by maximum overlap; ties are broken by head-token agreement.
4. **TLINK alignment.** Endpoints are aligned as canonical pairs, not surface mentions; relation types are normalized to `temporal_reasoning_profile.canonical_reltypes` on both sides.
5. **MEANTIME bridge alignment.** Structural only — surface spans are ignored (see [`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)).

## Why these rules

- They make metrics stable under tokenizer changes.
- They let the system be graded on the quality of its canonical reasoning layer, not on its preprocessing.
- They are consistent across evaluators, so numbers across phases can be compared honestly.

## Recording alignment decisions

Every evaluator run writes an `alignment.json` alongside its metrics file, enumerating:

- Which alignment mode was used.
- How many gold items had no aligned counterpart.
- How many system items had no aligned gold counterpart.

## See also

- [`datasets-overview.md`](datasets-overview.md)
- [`../55-evaluation-strategy/strategy-overview.md`](../55-evaluation-strategy/strategy-overview.md)
- [`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)
