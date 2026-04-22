# Evaluation Report

- Mode: batch
- Documents evaluated: 1
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.082 | 0.412 | 0.137 |
| micro | strict | event | 0.193 | 0.647 | 0.297 |
| micro | strict | timex | 0.154 | 0.500 | 0.235 |
| micro | strict | relation | 0.060 | 0.333 | 0.102 |
| micro | relaxed | entity | 0.118 | 0.588 | 0.196 |
| micro | relaxed | event | 0.211 | 0.706 | 0.324 |
| micro | relaxed | timex | 0.154 | 0.500 | 0.235 |
| micro | relaxed | relation | 0.060 | 0.333 | 0.102 |
| macro | strict | entity | 0.082 | 0.412 | 0.137 |
| macro | strict | event | 0.193 | 0.647 | 0.297 |
| macro | strict | timex | 0.154 | 0.500 | 0.235 |
| macro | strict | relation | 0.060 | 0.333 | 0.102 |
| macro | relaxed | entity | 0.118 | 0.588 | 0.196 |
| macro | relaxed | event | 0.211 | 0.706 | 0.324 |
| macro | relaxed | timex | 0.154 | 0.500 | 0.235 |
| macro | relaxed | relation | 0.060 | 0.333 | 0.102 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.297
- Strict TIMEX F1: 0.235
- Strict Relation F1: 0.102
- Composite: 0.220

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.027
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.008

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.137 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.297 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.102 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.235 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.193 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 76437

- Avg F1: 0.193
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 7 | 78 | 10 | 0.082 | 0.412 | 0.137 |
| event | 11 | 46 | 6 | 0.193 | 0.647 | 0.297 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 7 | 109 | 14 | 0.060 | 0.333 | 0.102 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.137) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.297) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.102) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (3 shown):
  - gold={'kind': 'entity', 'span': [79, 80, 81, 82, 83], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [79, 80], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [82, 83], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [83], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [97, 98, 99, 100, 101, 102], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [98, 99], 'attrs': {'syntactic_type': 'NOM'}}
- missing (7 shown):
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [19, 20], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [118, 119], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [95], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [95], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [121], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'authorize', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [50, 51], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- spurious (10 shown):
  - predicted={'kind': 'timex', 'span': [107], 'attrs': {'type': 'DATE', 'value': '2007-08-09'}}
  - predicted={'kind': 'timex', 'span': [146], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - predicted={'kind': 'timex', 'span': [168], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- endpoint_mismatch (2 shown):
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (73,), 'entity', (69,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (85,), 'entity', (79, 80, 81, 82, 83), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (85,), 'entity', (79, 80), (('sem_role', 'Arg0'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), (('sem_role', 'Arg1'),))
  - gold=('tlink', 'event', (14,), 'event', (37,), (('reltype', 'BEFORE'),))
- spurious (10 shown):
  - predicted=('clink', 'event', (230,), 'event', (233,), ())
  - predicted=('clink', 'event', (230,), 'event', (237,), ())
  - predicted=('clink', 'event', (233,), 'event', (237,), ())
