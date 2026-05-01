# NomBank Integration — CogComp Nominal SRL

**Status:** Completed (May 2026)  
**Service:** `cogcomp-nominal-srl` on port 8011  
**Branch:** `feature/entity-extraction-refinement-2026`

---

## What is NomBank?

[NomBank](https://nlp.cs.nyu.edu/meyers/NomBank.html) (Meyers et al., 2004) is a
corpus that annotates the argument structure of **nominal predicates** — nouns that
carry event or relational meaning. It is the nominal counterpart to
[PropBank](https://propbank.github.io/), which covers verbal predicates only.

### Why nominal predicates matter

English frequently nominalises events:

| Verbal form | Nominal form |
|-------------|--------------|
| *The company acquired Acme* | *the acquisition of Acme* |
| *The CEO resigned* | *the resignation of the CEO* |
| *The board decided* | *the board's decision* |

PropBank-only SRL misses all of the structure on the right column. With NomBank,
textgraphx can extract predicate–argument structure from noun phrases, capturing
a significant portion of the event content that would otherwise be invisible to
the pipeline.

---

## Service: cogcomp-nominal-srl

- **Endpoint:** `POST http://localhost:8011/predict_nom`
- **Predictor name:** `nombank-sense-srl`
- **License:** MIT (University of Illinois CogComp group)
- **Model backing:** fine-tuned on NomBank 1.0 over the Penn Treebank

### Request / Response shape

**Request:**
```json
{"sentence": "The acquisition of Acme was announced yesterday."}
```

**Response:**
```json
{
  "words": ["The", "acquisition", "of", "Acme", "was", "announced", "yesterday", "."],
  "frames": [
    {
      "predicate": "acquisition",
      "predicate_index": 1,
      "sense": "acquisition.01",
      "sense_score": 0.87,
      "tags": ["O", "B-V", "O", "B-ARG1", "O", "O", "O", "O"],
      "description": "[B-V acquisition] [B-ARG1 Acme]"
    }
  ]
}
```

Key fields per frame:

| Field | Meaning |
|-------|---------|
| `predicate` | Surface text of the nominal predicate |
| `predicate_index` | Token index of the predicate within `words` |
| `sense` | NomBank roleset id (e.g. `acquisition.01`) |
| `sense_score` | Float confidence for the sense assignment |
| `tags` | BIO sequence over `words`; `B-V` marks the predicate itself |

---

## Pipeline integration

### Config

`src/textgraphx/infrastructure/config.py` — `ServicesConfig.nom_srl_url`
defaults to `http://localhost:8011/predict_nom`.

### Call path

```
graph_based_nlp.py  →  callNominalSrlApi()  →  cogcomp service
                    ↓
              srl_processor.process_nominal_srl(doc, sentence_results)
                    ↓
              SRLProcessor._merge_frame(..., framework="NOMBANK")
              SRLProcessor._merge_frame_argument(...)
```

`graph_based_nlp.py` calls the service once per sentence and collects
`(sentence_token_offset, response)` pairs, then delegates to
`SRLProcessor.process_nominal_srl`.

### Graph output

Each nominal predicate produces:

- One **`Frame`** node with:
  - `framework = "NOMBANK"`
  - `sense` = NomBank roleset id (advisory-tier; only set when present)
  - `sense_conf` = confidence float (advisory-tier)
  - `headword`, `start_tok`, `end_tok`, `text` (canonical required fields)
- One **`FrameArgument`** node per non-V BIO span:
  - `type` = ARG0 / ARG1 / ARG2 / ARGM-* label
  - `head`, `start_tok`, `end_tok`, `text`
- **`PARTICIPANT`** and **`HAS_FRAME_ARGUMENT`** edges from each `FrameArgument`
  to its `Frame`
- **`PARTICIPATES_IN`** and **`IN_FRAME`** edges from `TagOccurrence` nodes to
  both the `Frame` and `FrameArgument` nodes

---

## NomBank argument roles

| Label | Typical role |
|-------|--------------|
| ARG0 | Agent / external argument (the entity performing / responsible) |
| ARG1 | Theme / internal argument (entity acted upon or described) |
| ARG2 | Benefactive, instrument, end state (sense-dependent) |
| ARGM-TMP | Temporal modifier |
| ARGM-LOC | Locative modifier |
| ARGM-MNR | Manner modifier |
| ARGM-CAU | Causal modifier |

Roles are sense-dependent; the NomBank roleset file for each lemma defines the
exact semantics of ARG2 and beyond.

---

## Evaluation results (May 2026)

Evaluated on 15 complex nominal examples in
`scripts/evaluation/data/srl_service_gold_dataset.json`:

| Mode | Examples matched |
|------|-----------------|
| Strict (exact BIO match) | 11 / 15 |
| Normalised (predicate identity + any argument overlap) | 14 / 15 |

Full report: `out/srl_service_eval_20260501T030245Z.json`

---

## Downstream pipeline benefits

| Phase | Benefit |
|-------|---------|
| **EventEnrichmentPhase** | Nominal frames with `framework=NOMBANK` are considered alongside verbal frames as event candidates; nouns like *resignation*, *acquisition*, *decision* now surface as `TEvent` candidates |
| **TemporalPhase** | Temporal arguments (`ARGM-TMP`) on nominal frames provide direct anchors for TIMEX linking |
| **TLINKs** | Nominal event nodes participate in `TLINK` inference alongside verbal events, increasing temporal relation coverage |
| **GraphRAG retrieval** | Querying `(f:Frame {framework:"NOMBANK"})` enables targeted retrieval of nominal event structure |

---

## Disabling the service

Set `nom_srl_url` to an empty string in config; `graph_based_nlp.py` skips the
call when the URL is absent, and `SRLProcessor.process_nominal_srl` is a no-op
when passed an empty list.
