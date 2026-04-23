<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Temporal Semantics

**Gateway** · **Wiki Home** · **Linguistics** · Temporal Semantics

## Abstract

Temporal semantics in TextGraphX follows ISO-TimeML conventions: time expressions (`TIMEX`), events (`TEvent` / `EventMention`), temporal signals (`Signal`), and typed temporal links (`TLINK`).

## What is represented

- **`TIMEX`** — canonical time expression. Carries ISO-TimeML attributes (`type`, `value`, `functionInDocument`, `mod`, ...).
- **`TimexMention`** — span-level evidence node for a TIMEX, linked via `REFERS_TO`.
- **`Signal`** — temporal signal node (e.g., *before*, *after*, *while*, *during*).
- **`TEvent`** — canonical event; carries tense/aspect/polarity/certainty/factuality attributes from the closed `event_attribute_vocabulary`.
- **`EventMention`** — span-level evidence for a `TEvent`.
- **`TLINK`** — typed temporal edge between `TEvent`/`TIMEX` endpoints. Relation types come from `temporal_reasoning_profile.canonical_reltypes` (Allen-aligned).

## Where it is produced

- Time expressions + signals: [`src/textgraphx/TemporalPhase.py`](../../../src/textgraphx/TemporalPhase.py) (TARSQI TTK-backed).
- Event enrichment: [`src/textgraphx/EventEnrichmentPhase.py`](../../../src/textgraphx/EventEnrichmentPhase.py).
- TLINK extraction: [`src/textgraphx/TlinksRecognizer.py`](../../../src/textgraphx/TlinksRecognizer.py).

## Why this matters

- ISO-TimeML value normalization is what allows cross-document comparisons and answerable "when" queries.
- DCT (document creation time) anchoring is the default when a deictic expression lacks an explicit anchor; policy is declared in `temporal_reasoning_profile.dct_anchor_policy`.
- Allen's interval algebra is the canonical substrate for consistency checks and conservative closure.

## Limits and pitfalls

- Narrative-time shifts and modality (hypotheticals, conditionals) are only partially modeled.
- Cross-document timeline alignment requires explicit anchoring; deictic normalization is not sufficient.

## References

- [pustejovsky2003timeml]
- [iso24617-1-2012]
- [allen1983intervals]
- [owl-time-2022]
- [tarsqi-ttk]

## See also

- [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)
- [`../30-algorithms/temporal-extraction-ttk.md`](../30-algorithms/temporal-extraction-ttk.md)
- [`../30-algorithms/tlink-rule-engine.md`](../30-algorithms/tlink-rule-engine.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
