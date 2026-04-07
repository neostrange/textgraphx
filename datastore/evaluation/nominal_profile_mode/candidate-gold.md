# Evaluation Report

- Mode: batch
- Documents evaluated: 1
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.070 | 0.471 | 0.122 |
| micro | strict | event | 0.000 | 0.000 | 0.000 |
| micro | strict | timex | 0.000 | 0.000 | 0.000 |
| micro | strict | relation | 0.000 | 0.000 | 0.000 |
| micro | relaxed | entity | 0.114 | 0.765 | 0.198 |
| micro | relaxed | event | 0.000 | 0.000 | 0.000 |
| micro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| micro | relaxed | relation | 0.000 | 0.000 | 0.000 |
| macro | strict | entity | 0.070 | 0.471 | 0.122 |
| macro | strict | event | 0.000 | 0.000 | 0.000 |
| macro | strict | timex | 0.000 | 0.000 | 0.000 |
| macro | strict | relation | 0.000 | 0.000 | 0.000 |
| macro | relaxed | entity | 0.114 | 0.765 | 0.198 |
| macro | relaxed | event | 0.000 | 0.000 | 0.000 |
| macro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| macro | relaxed | relation | 0.000 | 0.000 | 0.000 |

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.122 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- event: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- relation: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- relation: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.031 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 76437

- Avg F1: 0.031
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 8 | 106 | 9 | 0.070 | 0.471 | 0.122 |
| event | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.122) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- boundary_mismatch (5 shown):
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}} | predicted={'kind': 'entity', 'span': [24, 25, 26], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {}} | predicted={'kind': 'entity', 'span': [33, 34, 35, 36], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [72], 'attrs': {'syntactic_type': 'OTHER'}}
- missing (4 shown):
  - gold={'kind': 'entity', 'span': [57, 58, 59, 60, 61], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [82, 83], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [88], 'attrs': {'syntactic_type': 'PRO'}}
- spurious (5 shown):
  - predicted={'kind': 'entity', 'span': [5, 6], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [7, 8, 9, 10], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [19], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'functionInDocument': 'CREATION_TIME', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [15], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- missing (5 shown):
  - gold=('has_participant', 'event', (14,), 'entity', (11, 12, 13), ())
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), ())
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), ())
