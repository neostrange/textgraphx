<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Dataset Governance

**Gateway** · **Wiki Home** · **Datasets** · Governance

## Abstract

Datasets are first-class configuration. Paths, subset selections, and the ingestion fixture set are declared centrally so evaluations are reproducible.

## Where dataset paths live

- Central dataset configuration is maintained alongside the ingestion code; authoritative paths are not hard-coded inside evaluators.
- Fixtures and MEANTIME-derived inputs live under `src/textgraphx/datastore/` with subtrees reserved by purpose:
  - `datastore/annotated/` — user-owned annotated inputs (evaluation outputs must **not** land here).
  - `datastore/evaluation/` — all evaluation artifacts.
  - `datastore/fixtures/` — pinned fixtures for deterministic tests.
  - `datastore/tarsqi-dataset/` — TTK-consumable inputs.

## Governance rules

- No evaluator writes outside `datastore/evaluation/`.
- Dataset versions / subset identifiers are included in every self-certifying report.
- A new dataset requires: a page in `docs/wiki/70-datasets/`, an ingestion path, an alignment rule entry, and (if used for regression) a baseline seed PR.

## Privacy and licensing

- Third-party corpora are used under their respective licenses; redistribution is not implied by inclusion in documentation.
- Content derived from corpora for testing is either (a) non-substantive snippets acceptable under fair use or (b) synthesized.

## See also

- [`datasets-overview.md`](datasets-overview.md)
- [`gold-vs-system-alignment.md`](gold-vs-system-alignment.md)
- [`../55-evaluation-strategy/how-to-add-an-evaluator.md`](../55-evaluation-strategy/how-to-add-an-evaluator.md)
