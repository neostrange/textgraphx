# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.188 | 0.340 | 0.242 |
| micro | strict | event | 0.161 | 0.414 | 0.232 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 0.060 | 0.132 | 0.083 |
| micro | relaxed | entity | 0.220 | 0.408 | 0.286 |
| micro | relaxed | event | 0.211 | 0.541 | 0.303 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.030 | 0.132 | 0.049 |
| macro | strict | entity | 0.203 | 0.337 | 0.244 |
| macro | strict | event | 0.167 | 0.431 | 0.233 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 0.062 | 0.132 | 0.080 |
| macro | relaxed | entity | 0.239 | 0.420 | 0.294 |
| macro | relaxed | event | 0.218 | 0.564 | 0.305 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.031 | 0.132 | 0.048 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| tlink | 0.060 | 0.132 | 0.083 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.232
- Strict TIMEX F1: 0.379
- Strict Relation F1: 0.083
- Composite: 0.231

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.071
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.021

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: micro F1=0.286 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.303 below threshold 0.75 - mark as priority optimization track.
- relation: micro F1=0.049 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.526 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.189 | entity, event, timex, relation |
| 61327 | 0.235 | entity, event, timex, relation |
| 112579 | 0.266 | entity, event, timex, relation |
| 82738 | 0.332 | entity, event, timex, relation |
| 62405 | 0.343 | entity, event, relation |
| 96770 | 0.392 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.266
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 26 | 8 | 0.161 | 0.385 | 0.227 |
| event | 11 | 40 | 15 | 0.216 | 0.423 | 0.286 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 2 | 62 | 12 | 0.031 | 0.143 | 0.051 |

Suggested actions:
- entity: low F1 (0.227) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.286) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.051) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.500) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (26 shown):
  - predicted={'kind': 'entity', 'span': [12], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [74, 75], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [104, 105, 106], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (15 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (40 shown):
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
  - gold=('tlink', 'event', (73,), 'timex', (12, 13, 14, 15), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (87,), 'timex', (12, 13, 14, 15), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (51,), 'event', (67,), (('reltype', 'BEGINS'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (335,), 'timex', (334,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (211,), 'event', (262,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (322,), 'event', (332,), (('reltype', 'AFTER'),))

### Doc 61327

- Avg F1: 0.235
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 19 | 8 | 0.240 | 0.429 | 0.308 |
| event | 7 | 28 | 5 | 0.200 | 0.583 | 0.298 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 44 | 11 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.308) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.298) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
- spurious (19 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [33], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [86, 87], 'attrs': {'syntactic_type': 'PRO'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [58], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (28 shown):
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
  - gold=('tlink', 'event', (22,), 'event', (76,), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (76,), 'event', (87,), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (38,), 'timex', (37,), (('reltype', 'MEASURE'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (159,), 'timex', (161,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (171,), 'timex', (161,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (98,), 'event', (159,), (('reltype', 'BEFORE'),))

### Doc 62405

- Avg F1: 0.343
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 26 | 22 | 0.257 | 0.290 | 0.273 |
| event | 11 | 50 | 10 | 0.180 | 0.524 | 0.268 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 2 | 50 | 10 | 0.038 | 0.167 | 0.062 |

Suggested actions:
- entity: low F1 (0.273) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.268) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.062) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (22 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (26 shown):
  - predicted={'kind': 'entity', 'span': [8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [66, 67], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (50 shown):
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
  - gold=('tlink', 'event', (17,), 'event', (35,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (52,), 'timex', (56,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (17,), 'timex', (8, 9, 10, 11), (('reltype', 'BEFORE'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (246,), 'event', (264,), (('reltype', 'AFTER'),))
  - predicted=('tlink', 'event', (407,), 'event', (416,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (410,), 'timex', (66,), (('reltype', 'IS_INCLUDED'),))

### Doc 76437

- Avg F1: 0.189
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 36 | 13 | 0.100 | 0.235 | 0.140 |
| event | 12 | 44 | 5 | 0.214 | 0.706 | 0.329 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 3 | 99 | 8 | 0.029 | 0.273 | 0.053 |

Suggested actions:
- entity: low F1 (0.140) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.329) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.053) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (13 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (36 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (44 shown):
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
- missing (8 shown):
  - gold=('tlink', 'event', (37,), 'timex', (38, 39, 40, 41), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (104,), 'timex', (7, 8, 9, 10), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (49,), 'timex', (50, 51), (('reltype', 'ENDS'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (305,), 'timex', (302, 303), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (150,), 'event', (224,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (309,), 'timex', (302, 303), (('reltype', 'IS_INCLUDED'),))

### Doc 82738

- Avg F1: 0.332
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 31 | 5 | 0.114 | 0.444 | 0.182 |
| event | 12 | 46 | 3 | 0.207 | 0.800 | 0.329 |
| timex | 7 | 5 | 0 | 0.583 | 1.000 | 0.737 |
| relation | 2 | 32 | 13 | 0.059 | 0.133 | 0.082 |

Suggested actions:
- entity: low F1 (0.182) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.329) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.082) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.737) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (31 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [11], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [21], 'attrs': {'syntactic_type': 'PRO'}}
- event:
- missing (3 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [79], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'record', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (46 shown):
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
  - gold=('tlink', 'event', (43,), 'timex', (31, 32, 33), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (77,), 'event', (79,), (('reltype', 'ENDS'),))
  - gold=('tlink', 'event', (24,), 'timex', (11, 12, 13, 14), (('reltype', 'SIMULTANEOUS'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (221,), 'timex', (213,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (122,), 'event', (124,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (354,), 'timex', (25, 26), (('reltype', 'IS_INCLUDED'),))

### Doc 96770

- Avg F1: 0.392
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 14 | 11 | 5 | 0.560 | 0.737 | 0.636 |
| event | 7 | 17 | 13 | 0.292 | 0.350 | 0.318 |
| timex | 4 | 6 | 0 | 0.400 | 1.000 | 0.571 |
| relation | 1 | 35 | 12 | 0.028 | 0.077 | 0.041 |

Suggested actions:
- entity: low F1 (0.636) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.318) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.041) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.571) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (11 shown):
  - predicted={'kind': 'entity', 'span': [9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [36, 37, 38], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
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
  - gold=('tlink', 'event', (15,), 'event', (51,), (('reltype', 'INCLUDES'),))
  - gold=('tlink', 'event', (57,), 'event', (66,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (76,), 'event', (100,), (('reltype', 'BEGUN_BY'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (51,), 'event', (100,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (180,), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (255,), 'timex', (256,), (('reltype', 'IS_INCLUDED'),))
