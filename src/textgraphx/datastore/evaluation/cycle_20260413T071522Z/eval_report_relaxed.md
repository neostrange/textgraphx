# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.170 | 0.170 | 0.170 |
| micro | strict | event | 0.169 | 0.225 | 0.193 |
| micro | strict | timex | 0.266 | 0.548 | 0.358 |
| micro | strict | relation | 0.053 | 0.008 | 0.013 |
| micro | relaxed | entity | 0.292 | 0.292 | 0.292 |
| micro | relaxed | event | 0.243 | 0.324 | 0.278 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.026 | 0.008 | 0.012 |
| macro | strict | entity | 0.183 | 0.159 | 0.161 |
| macro | strict | event | 0.275 | 0.245 | 0.207 |
| macro | strict | timex | 0.300 | 0.562 | 0.379 |
| macro | strict | relation | 0.033 | 0.007 | 0.012 |
| macro | relaxed | entity | 0.327 | 0.296 | 0.295 |
| macro | relaxed | event | 0.378 | 0.352 | 0.294 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.017 | 0.007 | 0.010 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.000 | 0.000 | 0.000 |
| tlink | 0.053 | 0.013 | 0.021 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.193
- Strict TIMEX F1: 0.358
- Strict Relation F1: 0.013
- Composite: 0.189

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.085
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.025

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: micro F1=0.292 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.278 below threshold 0.75 - mark as priority optimization track.
- relation: micro F1=0.012 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.526 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.146 | entity, event, timex, relation |
| 61327 | 0.267 | entity, event, timex, relation |
| 112579 | 0.277 | entity, event, timex, relation |
| 96770 | 0.328 | entity, event, timex, relation |
| 62405 | 0.329 | entity, event, relation |
| 82738 | 0.338 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.277
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 11 | 9 | 0.267 | 0.308 | 0.286 |
| event | 5 | 0 | 21 | 1.000 | 0.192 | 0.323 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 0 | 4 | 23 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.286) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.323) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
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
  - predicted={'kind': 'entity', 'span': [175, 176, 177], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (21 shown):
  - gold={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [104], 'attrs': {'type': 'SET', 'value': 'P1W'}}
- spurious (9 shown):
  - predicted={'kind': 'timex', 'span': [277], 'attrs': {'type': 'DATE', 'value': '2008-09-03'}}
  - predicted={'kind': 'timex', 'span': [292], 'attrs': {'type': 'DATE', 'value': '2008-06'}}
  - predicted={'kind': 'timex', 'span': [294, 295], 'attrs': {'type': 'DATE', 'value': '2008'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (2,), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('tlink', 'event', (73,), 'timex', (12, 13, 14, 15), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (67,), 'event', (107,), (('reltype', 'AFTER'),))
- spurious (4 shown):
  - predicted=('tlink', 'event', (28,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (30,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (30,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))

### Doc 61327

- Avg F1: 0.267
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 10 | 10 | 0.333 | 0.333 | 0.333 |
| event | 5 | 8 | 7 | 0.385 | 0.417 | 0.400 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.333) - inspect extraction and matching rules for this layer.
- event: low F1 (0.400) - inspect extraction and matching rules for this layer.
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
- missing (7 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [38], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
- spurious (8 shown):
  - predicted={'kind': 'event', 'span': [192], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'estimate', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [222, 223], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'come', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [241], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'implement', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (3,), 'entity', (1, 2), (('sem_role', 'Arg1'),))
  - gold=('tlink', 'event', (22,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))

### Doc 62405

- Avg F1: 0.329
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 11 | 22 | 0.450 | 0.290 | 0.353 |
| event | 6 | 35 | 15 | 0.146 | 0.286 | 0.194 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.353) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.194) - inspect extraction and matching rules for this layer.
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
- missing (15 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (35 shown):
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'index', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [150], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'operation', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [152], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'default', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (84, 85), 'timex', (8, 9, 10, 11), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (52,), 'event', (84, 85), (('reltype', 'SIMULTANEOUS'),))
  - gold=('has_participant', 'event', (35,), 'entity', (27, 28, 29, 30, 31, 32, 33), (('sem_role', 'Arg0'),))

### Doc 76437

- Avg F1: 0.146
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 24 | 14 | 0.111 | 0.176 | 0.136 |
| event | 6 | 34 | 11 | 0.150 | 0.353 | 0.211 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 0 | 24 | 21 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.136) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.211) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (14 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (24 shown):
  - predicted={'kind': 'entity', 'span': [110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (11 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (34 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'authorize', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [134], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'addition', 'time': 'NON_FUTURE'}}
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
  - gold=('tlink', 'event', (62,), 'event', (104,), (('reltype', 'BEFORE'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (233,), 'timex', (225, 226), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (311,), 'timex', (302, 303), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (311,), 'timex', (302, 303), (('reltype', 'IS_INCLUDED'),))

### Doc 82738

- Avg F1: 0.338
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 15 | 6 | 0.167 | 0.333 | 0.222 |
| event | 10 | 26 | 5 | 0.278 | 0.667 | 0.392 |
| timex | 7 | 5 | 0 | 0.583 | 1.000 | 0.737 |
| relation | 0 | 0 | 22 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.222) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.392) - inspect extraction and matching rules for this layer.
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
  - predicted={'kind': 'entity', 'span': [7, 8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [51, 52], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [105], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- spurious (26 shown):
  - predicted={'kind': 'event', 'span': [108], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'approve', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [115], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [122], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attempt', 'time': 'NON_FUTURE'}}
- timex:
- spurious (5 shown):
  - predicted={'kind': 'timex', 'span': [112, 113], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [162, 163], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [213], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (48, 49), 'timex', (31, 32, 33), (('reltype', 'BEGUN_BY'),))
  - gold=('tlink', 'event', (43,), 'timex', (31, 32, 33), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (57,), 'timex', (11, 12, 13, 14), (('reltype', 'BEFORE'),))

### Doc 96770

- Avg F1: 0.328
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 7 | 4 | 14 | 0.636 | 0.333 | 0.437 |
| event | 4 | 9 | 16 | 0.308 | 0.200 | 0.242 |
| timex | 4 | 6 | 0 | 0.400 | 1.000 | 0.571 |
| relation | 1 | 9 | 22 | 0.100 | 0.043 | 0.061 |

Suggested actions:
- entity: low F1 (0.437) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.242) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.061) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.571) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (14 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (4 shown):
  - predicted={'kind': 'entity', 'span': [114, 115], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [134], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (16 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (9 shown):
  - predicted={'kind': 'event', 'span': [155], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'spread', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [161], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tighten', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [180], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'propose', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (38,), 'timex', (40, 41), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (76,), 'event', (100,), (('reltype', 'BEGUN_BY'),))
  - gold=('tlink', 'event', (68,), 'event', (76,), (('reltype', 'BEFORE'),))
- spurious (9 shown):
  - predicted=('tlink', 'event', (189, 190, 191), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (180,), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (255,), 'timex', (256,), (('reltype', 'IS_INCLUDED'),))
