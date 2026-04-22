# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.134 | 0.208 | 0.163 |
| micro | strict | event | 0.163 | 0.216 | 0.186 |
| micro | strict | timex | 0.273 | 0.194 | 0.226 |
| micro | strict | relation | 0.000 | 0.000 | 0.000 |
| micro | relaxed | entity | 0.195 | 0.305 | 0.238 |
| micro | relaxed | event | 0.197 | 0.261 | 0.225 |
| micro | relaxed | timex | 0.318 | 0.226 | 0.264 |
| micro | relaxed | relation | 0.000 | 0.000 | 0.000 |
| macro | strict | entity | 0.065 | 0.193 | 0.096 |
| macro | strict | event | 0.082 | 0.214 | 0.118 |
| macro | strict | timex | 0.089 | 0.194 | 0.122 |
| macro | strict | relation | 0.000 | 0.000 | 0.000 |
| macro | relaxed | entity | 0.097 | 0.291 | 0.144 |
| macro | relaxed | event | 0.099 | 0.255 | 0.142 |
| macro | relaxed | timex | 0.101 | 0.222 | 0.139 |
| macro | relaxed | relation | 0.000 | 0.000 | 0.000 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| tlink | 0.000 | 0.000 | 0.000 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.186
- Strict TIMEX F1: 0.226
- Strict Relation F1: 0.000
- Composite: 0.142

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.039
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.012

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: micro F1=0.238 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.225 below threshold 0.75 - mark as priority optimization track.
- relation: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.264 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.000 | entity, event, timex, relation |
| 82738 | 0.000 | entity, event, timex, relation |
| 96770 | 0.000 | entity, event, timex, relation |
| 62405 | 0.141 | entity, event, timex, relation |
| 61327 | 0.231 | entity, event, timex, relation |
| 112579 | 0.266 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.266
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 43 | 4 | 0.173 | 0.692 | 0.277 |
| event | 11 | 40 | 15 | 0.216 | 0.423 | 0.286 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 0 | 57 | 14 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.277) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.286) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.500) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (4 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [32], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (43 shown):
  - predicted={'kind': 'entity', 'span': [12], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [36, 37], 'attrs': {}}
  - predicted={'kind': 'entity', 'span': [46, 47], 'attrs': {'syntactic_type': 'NOM'}}
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
  - gold=('tlink', 'event', (67,), 'event', (107,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (73,), 'timex', (12, 13, 14, 15), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (36,), 'timex', (12, 13, 14, 15), (('reltype', 'IS_INCLUDED'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (322,), 'event', (332,), (('reltype', 'AFTER'),))
  - predicted=('tlink', 'event', (239,), 'event', (245,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (134,), 'event', (169,), (('reltype', ''),))

### Doc 61327

- Avg F1: 0.231
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 8 | 33 | 6 | 0.195 | 0.571 | 0.291 |
| event | 7 | 28 | 5 | 0.200 | 0.583 | 0.298 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 21 | 11 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.291) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.298) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (6 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [13, 14, 15], 'attrs': {}}
- spurious (33 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [33], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [52, 53, 54], 'attrs': {}}
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
  - gold=('tlink', 'event', (38,), 'event', (41,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (76,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (38,), 'timex', (37,), (('reltype', 'MEASURE'),))
- spurious (10 shown):
  - predicted=('tlink', 'event', (241,), 'event', (247,), (('reltype', ''),))
  - predicted=('tlink', 'event', (98,), 'event', (233,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (98,), 'event', (233,), (('reltype', 'BEFORE'),))

### Doc 62405

- Avg F1: 0.141
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 15 | 56 | 16 | 0.211 | 0.484 | 0.294 |
| event | 11 | 50 | 10 | 0.180 | 0.524 | 0.268 |
| timex | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 12 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.294) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.268) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (16 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [18, 19], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (56 shown):
  - predicted={'kind': 'entity', 'span': [8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [24, 25], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [66, 67], 'attrs': {'syntactic_type': 'NAM'}}
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
- missing (6 shown):
  - gold={'kind': 'timex', 'span': [8, 9, 10, 11], 'attrs': {'type': 'DATE', 'value': '2007-03-13'}}
  - gold={'kind': 'timex', 'span': [13, 14], 'attrs': {'type': 'DURATION', 'value': 'P2W'}}
  - gold={'kind': 'timex', 'span': [56], 'attrs': {'type': 'DATE', 'value': '2007-03-12'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (17,), 'event', (52,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (17,), 'event', (35,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (84, 85), 'timex', (8, 9, 10, 11), (('reltype', 'IS_INCLUDED'),))

### Doc 76437

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (17 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- event:
- missing (17 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [15], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (37,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (14,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (104,), 'timex', (7, 8, 9, 10), (('reltype', 'AFTER'),))

### Doc 82738

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 9 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 15 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 7 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 15 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (9 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
- event:
- missing (15 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumble', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- missing (7 shown):
  - gold={'kind': 'timex', 'span': [7, 8], 'attrs': {'type': 'DATE', 'value': '1987-10-20'}}
  - gold={'kind': 'timex', 'span': [11, 12, 13, 14], 'attrs': {'type': 'DATE', 'value': '2007-10-20'}}
  - gold={'kind': 'timex', 'span': [23], 'attrs': {'type': 'DATE', 'value': '2007-10-20'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (56,), 'event', (57,), (('reltype', 'BEGINS'),))
  - gold=('tlink', 'event', (57,), 'timex', (11, 12, 13, 14), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (48, 49), 'timex', (31, 32, 33), (('reltype', 'BEGUN_BY'),))

### Doc 96770

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 20 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 13 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (21 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
- event:
- missing (20 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [9, 10, 11, 12], 'attrs': {'type': 'DATE', 'value': '2008-01-21'}}
  - gold={'kind': 'timex', 'span': [21], 'attrs': {'type': 'DATE', 'value': '2008-01-21'}}
  - gold={'kind': 'timex', 'span': [40, 41], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- relation:
- missing (10 shown):
  - gold=('tlink', 'event', (92,), 'timex', (9, 10, 11, 12), (('reltype', 'INCLUDES'),))
  - gold=('tlink', 'event', (57,), 'event', (66,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (92,), 'event', (100,), (('reltype', 'SIMULTANEOUS'),))
