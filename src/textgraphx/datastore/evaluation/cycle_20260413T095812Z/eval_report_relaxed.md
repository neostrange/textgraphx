# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.264 | 0.264 | 0.264 |
| micro | strict | event | 0.162 | 0.405 | 0.232 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 0.154 | 0.031 | 0.051 |
| micro | relaxed | entity | 0.292 | 0.292 | 0.292 |
| micro | relaxed | event | 0.209 | 0.523 | 0.299 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.077 | 0.031 | 0.044 |
| macro | strict | entity | 0.290 | 0.266 | 0.262 |
| macro | strict | event | 0.174 | 0.424 | 0.238 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 0.106 | 0.030 | 0.045 |
| macro | relaxed | entity | 0.327 | 0.296 | 0.295 |
| macro | relaxed | event | 0.226 | 0.545 | 0.307 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.053 | 0.030 | 0.036 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.000 | 0.000 | 0.000 |
| tlink | 0.154 | 0.053 | 0.078 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.232
- Strict TIMEX F1: 0.379
- Strict Relation F1: 0.051
- Composite: 0.222

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.067
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.020

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: micro F1=0.292 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.299 below threshold 0.75 - mark as priority optimization track.
- relation: micro F1=0.044 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.526 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.182 | entity, event, timex, relation |
| 61327 | 0.254 | entity, event, timex, relation |
| 112579 | 0.310 | entity, event, timex, relation |
| 82738 | 0.315 | entity, event, timex, relation |
| 62405 | 0.337 | entity, event, relation |
| 96770 | 0.346 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.310
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 11 | 9 | 0.267 | 0.308 | 0.286 |
| event | 11 | 29 | 15 | 0.275 | 0.423 | 0.333 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 2 | 8 | 21 | 0.200 | 0.087 | 0.121 |

Suggested actions:
- entity: low F1 (0.286) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.333) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.121) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.500) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (9 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
- spurious (11 shown):
  - predicted={'kind': 'entity', 'span': [160, 161], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [166, 167], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [174, 175, 176, 177], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (15 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (29 shown):
  - predicted={'kind': 'event', 'span': [150], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'shed', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [167], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'investment', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [183], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'post', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
  - gold=('has_participant', 'event', (58,), 'entity', (55, 56, 57), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (30,), 'entity', (32, 33, 34), (('sem_role', 'Arg1'),))
- spurious (8 shown):
  - predicted=('tlink', 'event', (36,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (30,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (28,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))

### Doc 61327

- Avg F1: 0.254
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 10 | 10 | 0.333 | 0.333 | 0.333 |
| event | 7 | 21 | 5 | 0.250 | 0.583 | 0.350 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.333) - inspect extraction and matching rules for this layer.
- event: low F1 (0.350) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'NAM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [110], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [157, 158], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [58], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (21 shown):
  - predicted={'kind': 'event', 'span': [98], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'blame', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [100], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'slide', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [116], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'power', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
  - gold=('tlink', 'event', (38,), 'event', (50,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (76,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))
  - gold=('has_participant', 'event', (76,), 'entity', (63, 64, 65), (('sem_role', 'Arg1'),))

### Doc 62405

- Avg F1: 0.337
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 11 | 22 | 0.450 | 0.290 | 0.353 |
| event | 10 | 58 | 11 | 0.147 | 0.476 | 0.225 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.353) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.225) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (22 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (11 shown):
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [176, 177], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179, 180], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (11 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (58 shown):
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'index', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [147], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [149], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'sell', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (64,), 'timex', (66,), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (52,), 'event', (84, 85), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (96,), 'event', (109,), (('reltype', 'AFTER'),))

### Doc 76437

- Avg F1: 0.182
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 24 | 14 | 0.111 | 0.176 | 0.136 |
| event | 12 | 47 | 5 | 0.203 | 0.706 | 0.316 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 1 | 29 | 20 | 0.033 | 0.048 | 0.039 |

Suggested actions:
- entity: low F1 (0.136) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.316) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.039) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (14 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (24 shown):
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (47 shown):
  - predicted={'kind': 'event', 'span': [103], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'will', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (230,), 'timex', (225, 226), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (134,), 'timex', (107,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (436,), 'timex', (413, 414), (('reltype', 'IS_INCLUDED'),))

### Doc 82738

- Avg F1: 0.315
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 15 | 6 | 0.167 | 0.333 | 0.222 |
| event | 11 | 47 | 4 | 0.190 | 0.733 | 0.301 |
| timex | 7 | 5 | 0 | 0.583 | 1.000 | 0.737 |
| relation | 0 | 0 | 22 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.222) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.301) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.737) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (6 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (15 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [51, 52], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [105], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (4 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- spurious (47 shown):
  - predicted={'kind': 'event', 'span': [47], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'be', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [98], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'blame', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [101], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'loss', 'time': 'NON_FUTURE'}}
- timex:
- spurious (5 shown):
  - predicted={'kind': 'timex', 'span': [112, 113], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [162, 163], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [213], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'timex', (23,), 'timex', (31, 32, 33), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (77,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (16,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))

### Doc 96770

- Avg F1: 0.346
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 7 | 4 | 14 | 0.636 | 0.333 | 0.437 |
| event | 7 | 17 | 13 | 0.292 | 0.350 | 0.318 |
| timex | 4 | 6 | 0 | 0.400 | 1.000 | 0.571 |
| relation | 1 | 11 | 22 | 0.083 | 0.043 | 0.057 |

Suggested actions:
- entity: low F1 (0.437) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.318) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.057) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.571) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (14 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (4 shown):
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [134], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (13 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (17 shown):
  - predicted={'kind': 'event', 'span': [75], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'be', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [129], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'have', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (68,), 'event', (76,), (('reltype', 'BEFORE'),))
  - gold=('has_participant', 'event', (100,), 'entity', (99,), (('sem_role', 'Arg0'),))
  - gold=('tlink', 'event', (92,), 'timex', (9, 10, 11, 12), (('reltype', 'INCLUDES'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (32,), 'timex', (21,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (15,), 'timex', (21,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (255,), 'timex', (256,), (('reltype', 'IS_INCLUDED'),))
