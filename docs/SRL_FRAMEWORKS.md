# SRL Frameworks: PropBank and NomBank

**Scope:** This document describes the two SRL frameworks used by textgraphx, their role inventories, argument normalization rules, and light-verb construction handling.

---

## 1. Overview

textgraphx ingests Semantic Role Labeling (SRL) evidence from two frameworks:

| Framework | Service | Port | Predicate type |
|-----------|---------|------|----------------|
| **PropBank** | transformer-srl 2.4.6 | 8010 | Verbal predicates |
| **NomBank** | CogComp SRL-English | 8011 | Nominal predicates (deverbal nouns) |

Both frameworks share a numbered role inventory (`ARG0`–`ARG5`) and a set of adjunct modifier roles (`ARGM-*`). The numbered roles are defined relative to the predicate's roleset (e.g., `attack.01`: `ARG0 = Attacker`, `ARG1 = Target`).

---

## 2. PropBank (Verbal SRL)

**Service:** transformer-srl 2.4.6 at `http://localhost:8010/predict`

**Request format:**
```json
{ "sentence": "The company acquired a rival." }
```

**Response shape:**
```json
{
  "verbs": [
    {
      "verb": "acquired",
      "frame": "acquire.01",
      "frame_score": 0.93,
      "tags": ["B-ARG0", "I-ARG0", "B-V", "B-ARG1", "I-ARG1", "O"]
    }
  ],
  "words": ["The", "company", "acquired", "a", "rival", "."]
}
```

**Key fields:**
- `frame`: PropBank roleset id (e.g., `acquire.01`). Stored as `Frame.sense`.
- `frame_score`: Float confidence in `[0, 1]`. Stored as `Frame.sense_conf`.

**Legacy schema detection:** If the response contains `verbs[*].verb` but no `frame` field, this is the old AllenNLP format. A `WARNING` is logged; the frame is ingested without a roleset id.

---

## 3. NomBank (Nominal SRL)

**Service:** CogComp SRL-English at `http://localhost:8011/predict_nom`

**Request format:**
```json
{ "sentence": "The acquisition of a rival was completed." }
```

**Response shape:**
```json
{
  "words": ["The", "acquisition", "of", "a", "rival", "..."],
  "frames": [
    {
      "predicate": "acquisition",
      "predicate_index": 1,
      "sense": "acquisition.01",
      "sense_score": 0.85,
      "tags": ["O", "B-V", "O", "B-ARG1", "I-ARG1", "O"],
      "description": "acquisition.01: The act of acquiring something"
    }
  ]
}
```

**Key fields:**
- `sense`: NomBank roleset id. Stored as `Frame.sense`.
- `sense_score`: Float confidence. Stored as `Frame.sense_conf`.
- `predicate_index`: Token index of the nominal predicate head. Stored as `Frame.headTokenIndex`.

To disable nominal SRL: set `nom_srl_url = ""` in config or `TEXTGRAPHX_NOM_SRL_URL=""` in environment.

---

## 4. Argument Role Normalization

All raw role labels are normalized at ingestion time by `adapters/srl_role_normalizer.py`. The original label is always preserved as `raw_role` on the edge.

| Raw label | Canonical | Edge flags |
|-----------|-----------|-----------|
| `ARG0` | `ARG0` | — |
| `ARG1` | `ARG1` | — |
| `ARGM-TMP` | `ARGM-TMP` | — |
| `C-ARG1` | `ARG1` | `is_continuation=true` |
| `R-ARG0` | `ARG0` | `is_relative=true` |
| `ARG1-PRD` | `ARG1` | `predicative=true` |
| `ARGM-PRD` | `ARGM-PRD` | — |

Edge properties `is_continuation`, `is_relative`, and `predicative` are set only when `true` (never stored as `false`).

---

## 5. Cross-Framework Alignment (`ALIGNS_WITH`)

When a PROPBANK Frame and a NOMBANK Frame in the same document refer to the same situation, an optional `ALIGNS_WITH` edge is created between them.

**Alignment criteria:**
1. Both frames share the same `doc_id`.
2. Their `headword` strings match case-insensitively.
3. Their `headTokenIndex` values are within `TOKEN_WINDOW=5` tokens of each other.

**Edge properties:**
- `alignment_key`: deterministic key `align__<lo_id>__<hi_id>` (order-independent).
- `confidence`: geometric mean of `sense_conf` values; falls back to whichever value is available.

The alignment pass is run by `srl_frame_aligner.run_cross_framework_alignment(graph, doc_id)` after both SRL writer passes complete.

---

## 6. Light-Verb Constructions

When the verbal frame's headword is a light verb (`make`, `give`, `take`, `have`, `do`, `get`, `put`, `set`, `keep`) and an `ALIGNS_WITH` edge connects it to a nominal frame, the verbal frame's `is_light_verb_host` property is set to `true`.

In light-verb constructions the nominal argument carries the real event meaning. Downstream event enrichment should treat the nominal frame as the canonical `INSTANTIATES` source when `is_light_verb_host=true` on the verbal frame.

---

## 7. Confidence Gating

Frames are ingested regardless of confidence, but `Frame.provisional` is set to `true` when `sense_conf < config.ingestion.frame_confidence_min` (default `0.50`).

Downstream phases that require high-quality sense assignments should filter on `provisional = false` (or its absence, which also means not provisional).

---

## 8. Related Files

| File | Purpose |
|------|---------|
| `adapters/srl_role_normalizer.py` | `normalize_role()` — maps raw labels to `(canonical, raw, flags)` |
| `adapters/srl_frame_aligner.py` | `run_cross_framework_alignment()` — creates `ALIGNS_WITH` edges |
| `adapters/rest_caller.py` | `callAllenNlpApi()` — legacy-schema detection and HTTP calls |
| `text_processing_components/SRLProcessor.py` | `process_srl()`, `process_nominal_srl()`, `_merge_frame()`, `_link_argument_to_frame()` |
| `infrastructure/config.py` | `ServicesConfig.srl_url / nom_srl_url`, `IngestionConfig.frame_confidence_min` |
| `schema/migrations/0028_frame_srl_framework_indexes.cypher` | Indexes on `framework`, `sense`, `provisional`; backfill |
| `docs/COREF_POLICY.md` | Coreference backend decision |
