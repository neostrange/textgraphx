# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.219 | 0.349 | 0.269 |
| micro | strict | event | 0.166 | 0.414 | 0.237 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 0.071 | 0.107 | 0.085 |
| micro | relaxed | entity | 0.243 | 0.398 | 0.301 |
| micro | relaxed | event | 0.217 | 0.541 | 0.309 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.040 | 0.107 | 0.058 |
| macro | strict | entity | 0.238 | 0.345 | 0.271 |
| macro | strict | event | 0.171 | 0.431 | 0.238 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 0.077 | 0.101 | 0.084 |
| macro | relaxed | entity | 0.264 | 0.401 | 0.309 |
| macro | relaxed | event | 0.223 | 0.564 | 0.310 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.044 | 0.101 | 0.059 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.083 | 0.073 | 0.078 |
| tlink | 0.067 | 0.132 | 0.088 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.237
- Strict TIMEX F1: 0.379
- Strict Relation F1: 0.085
- Composite: 0.234

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.072
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.022

## Projection Determinism

- Deterministic: True
- Runs: 2
- Documents: 6/6 stable

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: micro F1=0.301 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.309 below threshold 0.75 - mark as priority optimization track.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.058 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.526 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.190 | entity, event, timex, relation |
| 61327 | 0.241 | entity, event, timex, relation |
| 112579 | 0.278 | entity, event, timex, relation |
| 82738 | 0.334 | entity, event, timex, relation |
| 62405 | 0.361 | entity, event, relation |
| 96770 | 0.401 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.278
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 22 | 8 | 0.185 | 0.385 | 0.250 |
| event | 11 | 38 | 15 | 0.224 | 0.423 | 0.293 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 3 | 64 | 20 | 0.045 | 0.130 | 0.067 |

Suggested actions:
- entity: low F1 (0.250) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.293) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.067) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.500) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (22 shown):
  - predicted={'kind': 'entity', 'span': [74], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [160, 161], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [166, 167], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (15 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (38 shown):
  - predicted={'kind': 'event', 'span': [34], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [93], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [116], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [104], 'attrs': {'type': 'SET', 'value': 'P1W'}}
- spurious (9 shown):
  - predicted={'kind': 'timex', 'span': [277], 'attrs': {'type': 'DATE', 'value': '2008-09-03'}}
  - predicted={'kind': 'timex', 'span': [292], 'attrs': {'type': 'DATE', 'value': '2008-06'}}
  - predicted={'kind': 'timex', 'span': [294, 295], 'attrs': {'type': 'DATE', 'value': '2008'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (103,), 'entity', (102,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (2,), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (107,), 'entity', (100,), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (116,), 'entity', (100,), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (187,), 'entity', (189,), (('sem_role', 'Arg2'),))

### Doc 61327

- Avg F1: 0.241
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 17 | 8 | 0.261 | 0.429 | 0.324 |
| event | 7 | 27 | 5 | 0.206 | 0.583 | 0.304 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 44 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.324) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.304) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
- spurious (17 shown):
  - predicted={'kind': 'entity', 'span': [86], 'attrs': {'syntactic_type': 'PRO'}}
  - predicted={'kind': 'entity', 'span': [110], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [58], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (27 shown):
  - predicted={'kind': 'event', 'span': [44], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [45], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [54], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [37], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
  - gold={'kind': 'timex', 'span': [91], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [47, 48], 'attrs': {'type': 'DATE', 'value': '2006-09-11'}}
  - predicted={'kind': 'timex', 'span': [161], 'attrs': {'type': 'DATE', 'value': '2007-02-26'}}
  - predicted={'kind': 'timex', 'span': [170], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (22,), 'entity', (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (3,), 'entity', (1, 2), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (151,), 'entity', (149,), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (159,), 'entity', (157, 158), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (184,), 'entity', (181, 182, 183), (('sem_role', 'Arg0'),))

### Doc 62405

- Avg F1: 0.361
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 22 | 22 | 0.290 | 0.290 | 0.290 |
| event | 11 | 47 | 10 | 0.190 | 0.524 | 0.278 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 4 | 45 | 22 | 0.082 | 0.154 | 0.107 |

Suggested actions:
- entity: low F1 (0.290) - inspect extraction and matching rules for this layer.
- event: low F1 (0.278) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.107) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (22 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (22 shown):
  - predicted={'kind': 'entity', 'span': [66], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [176, 177], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (47 shown):
  - predicted={'kind': 'event', 'span': [39], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'index', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [147], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (104,), 'entity', (107,), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (123,), 'entity', (121,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (137,), 'entity', (127, 128, 129, 130, 131, 132, 133, 134, 135), (('sem_role', 'Arg0'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (188,), 'entity', (184,), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (218,), 'entity', (202, 203, 204, 205), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (233,), 'entity', (202, 203, 204, 205), (('sem_role', 'Arg1'),))

### Doc 76437

- Avg F1: 0.190
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 34 | 13 | 0.105 | 0.235 | 0.145 |
| event | 12 | 43 | 5 | 0.218 | 0.706 | 0.333 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 3 | 109 | 18 | 0.027 | 0.143 | 0.045 |

Suggested actions:
- entity: low F1 (0.145) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.333) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.045) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (13 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (34 shown):
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [139], 'attrs': {'syntactic_type': 'PRO'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (43 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [121], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'authorize', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [50, 51], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- spurious (11 shown):
  - predicted={'kind': 'timex', 'span': [107], 'attrs': {'type': 'DATE', 'value': '2007-08-09'}}
  - predicted={'kind': 'timex', 'span': [146], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - predicted={'kind': 'timex', 'span': [168], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (14,), 'entity', (11, 12, 13), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (113,), 'entity', (109, 110, 111, 112), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (121,), 'entity', (122, 123, 124, 125), (('sem_role', 'Arg2'),))
  - predicted=('has_participant', 'event', (128,), 'entity', (122, 123, 124, 125), (('sem_role', 'Arg0'),))

### Doc 82738

- Avg F1: 0.334
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 25 | 6 | 0.107 | 0.333 | 0.162 |
| event | 12 | 45 | 3 | 0.211 | 0.800 | 0.333 |
| timex | 7 | 5 | 0 | 0.583 | 1.000 | 0.737 |
| relation | 3 | 33 | 19 | 0.083 | 0.136 | 0.103 |

Suggested actions:
- entity: low F1 (0.162) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.333) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.103) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.737) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (6 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (25 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [21], 'attrs': {'syntactic_type': 'PRO'}}
  - predicted={'kind': 'entity', 'span': [51, 52], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (3 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [79], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'record', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (45 shown):
  - predicted={'kind': 'event', 'span': [42], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [59], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [82], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
- timex:
- spurious (5 shown):
  - predicted={'kind': 'timex', 'span': [112, 113], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [162, 163], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [213], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (16,), 'entity', (15,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (4,), 'entity', (1, 2, 3), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (43,), 'entity', (35, 36, 37, 38, 39, 40, 41, 42), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (180,), 'entity', (181, 182), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (185,), 'entity', (181, 182), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (383,), 'entity', (377,), (('sem_role', 'Arg1'),))

### Doc 96770

- Avg F1: 0.401
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 14 | 8 | 5 | 0.636 | 0.737 | 0.683 |
| event | 7 | 17 | 13 | 0.292 | 0.350 | 0.318 |
| timex | 4 | 6 | 0 | 0.400 | 1.000 | 0.571 |
| relation | 1 | 39 | 22 | 0.025 | 0.043 | 0.032 |

Suggested actions:
- entity: low F1 (0.683) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.318) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.032) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.571) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (8 shown):
  - predicted={'kind': 'entity', 'span': [36, 37, 38], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [134], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (13 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (17 shown):
  - predicted={'kind': 'event', 'span': [120], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [142], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'begin', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (100,), 'entity', (99,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (107,), 'entity', (109, 110, 111), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (15,), 'entity', (13, 14), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (120,), 'entity', (113, 114, 115), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (143,), 'entity', (144, 145), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (180,), 'entity', (179,), (('sem_role', 'Arg0'),))
