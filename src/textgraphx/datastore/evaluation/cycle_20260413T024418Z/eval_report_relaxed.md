# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.128 | 0.283 | 0.176 |
| micro | strict | event | 0.168 | 0.360 | 0.229 |
| micro | strict | timex | 0.266 | 0.548 | 0.358 |
| micro | strict | relation | 0.052 | 0.107 | 0.070 |
| micro | relaxed | entity | 0.179 | 0.396 | 0.247 |
| micro | relaxed | event | 0.235 | 0.505 | 0.321 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.053 | 0.107 | 0.071 |
| macro | strict | entity | 0.151 | 0.290 | 0.184 |
| macro | strict | event | 0.177 | 0.370 | 0.230 |
| macro | strict | timex | 0.300 | 0.562 | 0.379 |
| macro | strict | relation | 0.056 | 0.103 | 0.069 |
| macro | relaxed | entity | 0.207 | 0.418 | 0.257 |
| macro | relaxed | event | 0.247 | 0.518 | 0.321 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.056 | 0.103 | 0.069 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.043 | 0.182 | 0.069 |
| tlink | 0.121 | 0.053 | 0.073 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.229
- Strict TIMEX F1: 0.358
- Strict Relation F1: 0.070
- Composite: 0.220

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.092
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.028

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.247 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.321 below threshold 0.75 - mark as priority optimization track.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.071 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: micro F1=0.526 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.211 | entity, event, timex, relation |
| 61327 | 0.213 | entity, event, timex, relation |
| 112579 | 0.298 | entity, event, timex, relation |
| 82738 | 0.320 | entity, event, timex, relation |
| 62405 | 0.344 | entity, event, relation |
| 96770 | 0.370 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.298
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 32 | 7 | 0.158 | 0.462 | 0.235 |
| event | 11 | 26 | 15 | 0.297 | 0.423 | 0.349 |
| timex | 5 | 9 | 1 | 0.357 | 0.833 | 0.500 |
| relation | 3 | 30 | 20 | 0.091 | 0.130 | 0.107 |

Suggested actions:
- entity: low F1 (0.235) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.349) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.107) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.500) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (7 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [12], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [74, 75], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [76, 77, 78], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [32, 33, 34], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [141, 142], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'remain', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [150], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'shed', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [104], 'attrs': {'type': 'SET', 'value': 'P1W'}}
- spurious (9 shown):
  - predicted={'kind': 'timex', 'span': [277], 'attrs': {'type': 'DATE', 'value': '2008-09-03'}}
  - predicted={'kind': 'timex', 'span': [292], 'attrs': {'type': 'DATE', 'value': '2008-06'}}
  - predicted={'kind': 'timex', 'span': [294, 295], 'attrs': {'type': 'DATE', 'value': '2008'}}
- relation:
- endpoint_mismatch (2 shown):
  - gold=('has_participant', 'event', (103,), 'entity', (102,), ()) | predicted=('has_participant', 'event', (103,), 'entity', (102, 103, 104, 105, 106), ())
  - gold=('has_participant', 'event', (36,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), ()) | predicted=('has_participant', 'event', (36,), 'entity', (16, 17, 18, 19, 20), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (2,), 'entity', (1,), ())
  - gold=('has_participant', 'event', (26,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), ())
  - gold=('has_participant', 'event', (30,), 'entity', (32, 33, 34), ())
- spurious (10 shown):
  - predicted=('has_participant', 'event', (141, 142), 'entity', (138, 139, 140), ())
  - predicted=('has_participant', 'event', (150,), 'entity', (138, 139, 140), ())
  - predicted=('has_participant', 'event', (150,), 'entity', (151,), ())

### Doc 61327

- Avg F1: 0.213
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 25 | 9 | 0.194 | 0.400 | 0.261 |
| event | 5 | 22 | 7 | 0.185 | 0.417 | 0.256 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 24 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.261) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.256) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72, 73, 74], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [70], 'attrs': {'syntactic_type': 'NAM'}}
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'NAM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [86, 87], 'attrs': {'syntactic_type': 'PRO'}}
  - predicted={'kind': 'entity', 'span': [100, 101], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- boundary_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [38], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [36, 37, 38], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [92], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [89, 90, 91, 92], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}}
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [58], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [98], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'blame', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [100], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'slide', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [113, 114], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [37], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
  - gold={'kind': 'timex', 'span': [91], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [47, 48], 'attrs': {'type': 'DATE', 'value': '2006-09-11'}}
  - predicted={'kind': 'timex', 'span': [161], 'attrs': {'type': 'DATE', 'value': '2007-02-26'}}
  - predicted={'kind': 'timex', 'span': [170], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- relation:
- endpoint_mismatch (2 shown):
  - gold=('has_participant', 'event', (22,), 'entity', (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), ()) | predicted=('has_participant', 'event', (22,), 'entity', (13,), ())
  - gold=('has_participant', 'event', (3,), 'entity', (1, 2), ()) | predicted=('has_participant', 'event', (3,), 'entity', (1,), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), ())
  - gold=('has_participant', 'event', (58,), 'entity', (60, 61), ())
  - gold=('has_participant', 'event', (76,), 'entity', (63, 64, 65), ())
- spurious (10 shown):
  - predicted=('has_participant', 'event', (116,), 'entity', (110,), ())
  - predicted=('has_participant', 'event', (141, 142, 143), 'entity', (132, 133, 134, 135, 136, 137, 138, 139), ())
  - predicted=('has_participant', 'event', (151,), 'entity', (148, 149), ())

### Doc 62405

- Avg F1: 0.344
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 11 | 32 | 20 | 0.256 | 0.355 | 0.297 |
| event | 10 | 46 | 11 | 0.179 | 0.476 | 0.260 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 2 | 53 | 24 | 0.036 | 0.077 | 0.049 |

Suggested actions:
- entity: low F1 (0.297) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.260) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.049) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [66, 67], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [38, 39], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'index', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [147], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}
- relation:
- endpoint_mismatch (3 shown):
  - gold=('has_participant', 'event', (35,), 'entity', (27, 28, 29, 30, 31, 32, 33), ()) | predicted=('has_participant', 'event', (35,), 'entity', (24, 25, 26, 27, 28, 29), ())
  - gold=('has_participant', 'event', (52,), 'entity', (44, 45, 46, 47, 48, 49, 50), ()) | predicted=('has_participant', 'event', (52,), 'entity', (47,), ())
  - gold=('has_participant', 'event', (84, 85), 'entity', (68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82), ()) | predicted=('has_participant', 'event', (84,), 'entity', (68, 69, 70), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (104,), 'entity', (107,), ())
  - gold=('has_participant', 'event', (123,), 'entity', (121,), ())
  - gold=('has_participant', 'event', (137,), 'entity', (127, 128, 129, 130, 131, 132, 133, 134, 135), ())
- spurious (10 shown):
  - predicted=('has_participant', 'event', (109,), 'entity', (107,), ())
  - predicted=('has_participant', 'event', (147,), 'entity', (140, 141, 142, 143, 144, 145), ())
  - predicted=('has_participant', 'event', (147,), 'entity', (150,), ())

### Doc 76437

- Avg F1: 0.211
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 53 | 11 | 0.102 | 0.353 | 0.158 |
| event | 12 | 39 | 5 | 0.235 | 0.706 | 0.353 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 5 | 77 | 16 | 0.061 | 0.238 | 0.097 |

Suggested actions:
- entity: low F1 (0.158) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.353) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.097) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'authorize', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [134], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'addition', 'time': 'NON_FUTURE'}}
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
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), ()) | predicted=('has_participant', 'event', (73,), 'entity', (69, 70, 71), ())
  - gold=('has_participant', 'event', (85,), 'entity', (88, 89, 90), ()) | predicted=('has_participant', 'event', (85,), 'entity', (88, 89), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), ())
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), ())
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), ())
- spurious (10 shown):
  - predicted=('has_participant', 'event', (113,), 'entity', (118, 119), ())
  - predicted=('has_participant', 'event', (128,), 'entity', (136, 137), ())
  - predicted=('has_participant', 'event', (150,), 'entity', (148, 149), ())

### Doc 82738

- Avg F1: 0.320
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 39 | 4 | 0.114 | 0.556 | 0.189 |
| event | 11 | 36 | 4 | 0.234 | 0.733 | 0.355 |
| timex | 7 | 5 | 0 | 0.583 | 1.000 | 0.737 |
| relation | 0 | 45 | 22 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.189) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.355) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.737) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (4 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [11], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [21, 22], 'attrs': {'syntactic_type': 'PRO'}}
- event:
- missing (4 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [98], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'blame', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [101], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'loss', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [108], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'approve', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- timex:
- spurious (5 shown):
  - predicted={'kind': 'timex', 'span': [112, 113], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [162, 163], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [213], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}
- relation:
- endpoint_mismatch (5 shown):
  - gold=('has_participant', 'event', (4,), 'entity', (1, 2, 3), ()) | predicted=('has_participant', 'event', (4,), 'entity', (1,), ())
  - gold=('has_participant', 'event', (43,), 'entity', (35, 36, 37, 38, 39, 40, 41, 42), ()) | predicted=('has_participant', 'event', (43,), 'entity', (36, 37), ())
  - gold=('has_participant', 'event', (60, 61), 'entity', (58, 59), ()) | predicted=('has_participant', 'event', (60,), 'entity', (59, 60), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (16,), 'entity', (15,), ())
  - gold=('has_participant', 'event', (77,), 'entity', (73, 74, 75), ())
  - gold=('tlink', 'event', (16,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (108,), 'entity', (105,), ())
  - predicted=('has_participant', 'event', (115,), 'entity', (116, 117), ())
  - predicted=('has_participant', 'event', (124, 125), 'entity', (126,), ())

### Doc 96770

- Avg F1: 0.370
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 8 | 11 | 13 | 0.421 | 0.381 | 0.400 |
| event | 7 | 13 | 13 | 0.350 | 0.350 | 0.350 |
| timex | 4 | 6 | 0 | 0.400 | 1.000 | 0.571 |
| relation | 4 | 23 | 19 | 0.148 | 0.174 | 0.160 |

Suggested actions:
- entity: low F1 (0.400) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.350) - inspect extraction and matching rules for this layer.
- relation: low F1 (0.160) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.571) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [142], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'begin', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [155], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'spread', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- endpoint_mismatch (1 shown):
  - gold=('has_participant', 'event', (51,), 'entity', (47, 48, 49, 50), ()) | predicted=('has_participant', 'event', (51,), 'entity', (48, 49), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (107,), 'entity', (109, 110, 111), ())
  - gold=('has_participant', 'event', (15,), 'entity', (18, 19, 20), ())
  - gold=('has_participant', 'event', (24,), 'entity', (29, 30, 31), ())
- spurious (10 shown):
  - predicted=('has_participant', 'event', (100,), 'entity', (101, 102), ())
  - predicted=('has_participant', 'event', (100,), 'entity', (106, 107), ())
  - predicted=('has_participant', 'event', (130,), 'entity', (126, 127), ())
