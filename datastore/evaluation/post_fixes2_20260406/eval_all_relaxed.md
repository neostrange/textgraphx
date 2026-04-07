# Evaluation Report

- Mode: batch
- Documents evaluated: 1
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.000 | 0.000 | 0.000 |
| micro | strict | event | 0.149 | 0.647 | 0.242 |
| micro | strict | timex | 0.000 | 0.000 | 0.000 |
| micro | strict | relation | 0.075 | 0.333 | 0.123 |
| micro | relaxed | entity | 0.064 | 0.176 | 0.094 |
| micro | relaxed | event | 0.176 | 0.765 | 0.286 |
| micro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| micro | relaxed | relation | 0.075 | 0.333 | 0.123 |
| macro | strict | entity | 0.000 | 0.000 | 0.000 |
| macro | strict | event | 0.149 | 0.647 | 0.242 |
| macro | strict | timex | 0.000 | 0.000 | 0.000 |
| macro | strict | relation | 0.075 | 0.333 | 0.123 |
| macro | relaxed | entity | 0.064 | 0.176 | 0.094 |
| macro | relaxed | event | 0.176 | 0.765 | 0.286 |
| macro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| macro | relaxed | relation | 0.075 | 0.333 | 0.123 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.242
- Strict TIMEX F1: 0.000
- Strict Relation F1: 0.123
- Composite: 0.134

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.044
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.013

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.094 below threshold 0.50 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.286 below threshold 0.50 - mark as priority optimization track.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.123 below threshold 0.50 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.000 below threshold 0.50 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.126 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 76437

- Avg F1: 0.126
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 44 | 14 | 0.064 | 0.176 | 0.094 |
| event | 13 | 61 | 4 | 0.176 | 0.765 | 0.286 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 7 | 86 | 14 | 0.075 | 0.333 | 0.123 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.094) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.286) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.123) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- boundary_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [72], 'attrs': {'ent_class': 'GEN', 'syntactic_type': 'PTV'}}
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (5 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9, 10], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [44, 45, 46], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [53, 54], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'PTV'}}
- event:
- missing (4 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (5 shown):
  - predicted={'kind': 'event', 'span': [84], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'are', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [103], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'will', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'functionInDocument': 'CREATION_TIME', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [15], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- endpoint_mismatch (1 shown):
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), ()) | predicted=('has_participant', 'event', (73,), 'entity', (69, 70, 71), ())
- missing (5 shown):
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), ())
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), ())
  - gold=('tlink', 'event', (14,), 'event', (37,), (('reltype', 'BEFORE'),))
- spurious (5 shown):
  - predicted=('clink', 'event', (230,), 'event', (233,), ())
  - predicted=('clink', 'event', (230,), 'event', (237,), ())
  - predicted=('clink', 'event', (233,), 'event', (237,), ())
