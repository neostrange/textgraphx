# scripts/evaluation

This directory holds **evaluation harness scripts** for assessing pipeline output quality.

These scripts are actively maintained and are intended for use alongside the formal evaluation
infrastructure in `src/textgraphx/evaluation/`.

## Scripts

| Script | Purpose |
|---|---|
| `evaluate_entity_spans.py` | Entity span precision/recall evaluation |
| `evaluate_event_bound.py` | Event boundary evaluation |
| `evaluate_event_nodes.py` | Event node coverage evaluation |
| `evaluate_event_xml.py`, `evaluate_event_xml2.py` | Event extraction evaluated against XML gold |
| `evaluate_noise.py` | Noise/false-positive analysis |
| `evaluate_outputs.py`, `evaluate_outputs_batch.py` | Full pipeline output evaluation |
| `evaluate_relation_spans.py` | Relation span evaluation |
| `evaluate_slink.py` | Subordinate link (SLINK) evaluation |
| `evaluate_wordnet_nominals.py` | WordNet nominal coverage evaluation |
| `evaluate_ab_clink.sh` | A/B evaluation shell runner for clinks |
| `evaluate_batch_baseline.sh` | Batch baseline evaluation shell runner |
| `evaluate_test.py` | Quick evaluation sanity check |
| `eval_print*.py` | Pretty-print evaluation reports from JSON output |

## Usage

Most scripts expect a running Neo4j instance and evaluation JSON outputs under
`src/textgraphx/datastore/evaluation/`. See the main `docs/` folder for evaluation workflow
documentation.

Retention policy (repo hygiene):

- `src/textgraphx/datastore/evaluation/latest/` is the mutable latest snapshot location.
- `src/textgraphx/datastore/evaluation/baseline/` stores curated baseline snapshots used for comparison.
- Refreshing the baseline with `scripts/run_quality_baseline.sh` now emits `kg_quality_comparison.json` when a prior baseline exists; review that delta before committing the refreshed snapshot.
- Historical `cycle_*` runs should not be committed; archive externally when needed.
