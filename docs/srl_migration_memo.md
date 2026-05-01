# SRL Migration Memo: AllenNLP → transformer-srl

**Status:** Completed (May 2026)  
**Branch:** `feature/entity-extraction-refinement-2026`

---

## Why we migrated

The legacy AllenNLP `srl-bert` service (port 8000) was replaced with
[transformer-srl 2.4.6](https://github.com/Riccorl/transformer-srl) (port 8010)
for three reasons:

1. **Better extraction quality** — head-to-head evaluation on a 15-sentence complex
   PropBank gold dataset shows the new service outperforms the legacy one at every
   metric (see §Evaluation Results below).
2. **Richer output** — the new service returns a PropBank sense id (`frame`) and a
   confidence score (`frame_score`) per verbal predicate; the legacy service returned
   only BIO role tags.
3. **License** — both services are MIT-licensed; the new service removes the
   AllenNLP Apache-2.0 + research-use restriction ambiguity.

---

## Evaluation Results

Evaluation was conducted on
`scripts/evaluation/data/srl_service_gold_dataset.json`
(15 verbal PropBank examples with complex nested argument structure).
Strict BIO-tag F1 reported at token level.

| Service | Precision | Recall | F1 | TP | FP | FN |
|---------|-----------|--------|----|----|----|----|
| **transformer-srl 2.4.6** (new) | 0.8919 | 0.9706 | **0.9296** | 66 | 8 | 2 |
| AllenNLP srl-bert (legacy) | 0.8784 | 0.9559 | 0.9155 | 65 | 9 | 3 |

Full machine-readable reports:

- `out/verbal_srl_compare_20260501T030818Z.json` — per-example breakdown
- `out/verbal_srl_compare_20260501T030818Z.md` — human-readable summary
- `out/srl_service_eval_20260501T030245Z.json` — detailed evaluation with latency

---

## What changed in the graph

Each `Frame` node now carries two additional advisory-tier properties when the
verbal SRL service provides them:

| Property | Type | Source | Example |
|----------|------|--------|---------|
| `sense` | `string` | `frame` field in service response | `"run.02"` |
| `sense_conf` | `float` | `frame_score` field in service response | `0.9437` |
| `framework` | `string` | always `"PROPBANK"` for verbal SRL | `"PROPBANK"` |

These properties are persisted via `SRLProcessor._merge_frame()` using a
`FOREACH`-guarded `SET` so that nodes created by the legacy path (no sense
output) are not affected.

---

## Code changes

| File | Change |
|------|--------|
| `src/textgraphx/adapters/semantic_role_labeler.py` | `extract_srl()` now reads `frame` and `frame_score` from the service response and stores them under `__frame__` / `__frame_score__` keys in `tok._.SRL` |
| `src/textgraphx/text_processing_components/SRLProcessor.py` | `process_srl()` reads `__frame__` / `__frame_score__` before the role loop and passes them as `sense` / `sense_conf` to `_merge_frame()` |
| `src/textgraphx/infrastructure/config.py` | `ServicesConfig.srl_url` updated to `http://localhost:8010/predict` |

---

## Backward compatibility

- The `srl_url` config key continues to control the endpoint; switching back
  to the legacy service requires only a config change.
- If the service does not return `frame` / `frame_score` (e.g., legacy
  AllenNLP), those fields are absent from `tok._.SRL` and `_merge_frame` is
  called with `sense=None`, `sense_conf=None` — no graph change.
- The `__frame__` / `__frame_score__` dict keys are filtered out before role
  iteration, so no existing role-parsing logic is affected.
