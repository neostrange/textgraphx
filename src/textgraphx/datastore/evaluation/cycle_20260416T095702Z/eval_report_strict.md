# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.087 | 0.349 | 0.140 |
| micro | strict | event | 0.134 | 0.351 | 0.195 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 1.000 | 1.000 | 1.000 |
| micro | relaxed | entity | 0.147 | 0.585 | 0.234 |
| micro | relaxed | event | 0.203 | 0.532 | 0.294 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 1.000 | 1.000 | 1.000 |
| macro | strict | entity | 0.094 | 0.350 | 0.144 |
| macro | strict | event | 0.147 | 0.361 | 0.202 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 1.000 | 1.000 | 1.000 |
| macro | relaxed | entity | 0.160 | 0.576 | 0.244 |
| macro | relaxed | event | 0.215 | 0.546 | 0.299 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 1.000 | 1.000 | 1.000 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| tlink | 1.000 | 1.000 | 1.000 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.195
- Strict TIMEX F1: 0.379
- Strict Relation F1: 1.000
- Composite: 0.491

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.100
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.030

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.140 below threshold 0.75 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.195 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- timex: micro F1=0.379 below threshold 0.75 - mark as priority optimization track.
- timex: type mismatch volume present - refine schema mapping and attribute projection.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.335 | entity, event, timex |
| 82738 | 0.368 | entity, event, timex |
| 61327 | 0.427 | entity, event, timex |
| 112579 | 0.442 | entity, event, timex |
| 96770 | 0.485 | entity, event, timex |
| 62405 | 0.555 | entity, event |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.442
- Weak layers: entity, event, timex

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 7 | 63 | 6 | 0.100 | 0.538 | 0.169 |
| event | 8 | 46 | 18 | 0.148 | 0.308 | 0.200 |
| timex | 4 | 10 | 2 | 0.286 | 0.667 | 0.400 |
| relation | 14 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.169) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.200) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.400) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}} | predicted={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [32], 'attrs': {'syntactic_type': 'NOM'}}
- missing (4 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [32], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (61 shown):
  - predicted={'kind': 'entity', 'span': [3], 'attrs': {'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [12], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [37], 'attrs': {'syntactic_type': 'PTV'}}
- event:
- type_mismatch (5 shown):
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [30], 'attrs': {'aspect': 'NONE', 'pos': 'NOUN', 'pred': 'performance', 'tense': 'NONE'}} | predicted={'kind': 'event', 'span': [30], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'performance', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [69], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [69], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'time': 'NON_FUTURE'}}
- missing (13 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [42], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'trading', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (41 shown):
  - predicted={'kind': 'event', 'span': [34], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [93], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [116], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- timex:
- type_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [125], 'attrs': {'type': 'DURATION', 'value': 'PY5'}} | predicted={'kind': 'timex', 'span': [125], 'attrs': {'type': 'DURATION', 'value': 'P5Y'}}
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [104], 'attrs': {'type': 'SET', 'value': 'P1W'}}
- spurious (9 shown):
  - predicted={'kind': 'timex', 'span': [277], 'attrs': {'type': 'DATE', 'value': '2008-09-03'}}
  - predicted={'kind': 'timex', 'span': [292], 'attrs': {'type': 'DATE', 'value': '2008-06'}}
  - predicted={'kind': 'timex', 'span': [294, 295], 'attrs': {'type': 'DATE', 'value': '2008'}}

### Doc 61327

- Avg F1: 0.427
- Weak layers: entity, event, timex

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 49 | 11 | 0.075 | 0.267 | 0.118 |
| event | 6 | 29 | 6 | 0.171 | 0.500 | 0.255 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.118) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.255) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}} | predicted={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [63, 64, 65], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [64, 65], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [69, 70], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [70], 'attrs': {'syntactic_type': 'NAM'}}
- missing (7 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14, 15], 'attrs': {}}
- spurious (45 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [24, 25, 26], 'attrs': {'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [33], 'attrs': {'syntactic_type': 'PTV'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attacks', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'time': 'NON_FUTURE'}}
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

### Doc 62405

- Avg F1: 0.555
- Weak layers: entity, event

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 11 | 65 | 20 | 0.145 | 0.355 | 0.206 |
| event | 10 | 50 | 11 | 0.167 | 0.476 | 0.247 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.206) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.247) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [27, 28], 'attrs': {'syntactic_type': 'PRE.NOM'}} | predicted={'kind': 'entity', 'span': [27, 28, 29], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [44, 45, 46, 47, 48, 49, 50], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [45], 'attrs': {'syntactic_type': 'PTV'}}
  - gold={'kind': 'entity', 'span': [127, 128, 129, 130, 131, 132, 133, 134, 135], 'attrs': {}} | predicted={'kind': 'entity', 'span': [135], 'attrs': {'syntactic_type': 'NOM'}}
- type_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [101], 'attrs': {}} | predicted={'kind': 'entity', 'span': [101], 'attrs': {'syntactic_type': 'NOM'}}
- missing (15 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [18, 19], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (60 shown):
  - predicted={'kind': 'entity', 'span': [8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [12, 13, 14], 'attrs': {'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [24, 25], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [84], 'attrs': {}} | predicted={'kind': 'event', 'span': [84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- missing (10 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (49 shown):
  - predicted={'kind': 'event', 'span': [39], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'index', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [147], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}

### Doc 76437

- Avg F1: 0.335
- Weak layers: entity, event, timex

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 94 | 14 | 0.031 | 0.176 | 0.053 |
| event | 2 | 56 | 15 | 0.034 | 0.118 | 0.053 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.053) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.053) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [79, 80, 81, 82, 83], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [83], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [97, 98, 99, 100, 101, 102], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [98, 99], 'attrs': {'syntactic_type': 'NOM'}}
- type_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {}} | predicted={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {'syntactic_type': 'NAM'}}
- missing (11 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (91 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [40, 41], 'attrs': {'syntactic_type': 'PTV'}}
- event:
- type_mismatch (6 shown):
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [37], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'rebound', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [37], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'rebound', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [62], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [62], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- missing (9 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (50 shown):
  - predicted={'kind': 'event', 'span': [39], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'in', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [44], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'more', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [52], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'down', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [50, 51], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- spurious (11 shown):
  - predicted={'kind': 'timex', 'span': [107], 'attrs': {'type': 'DATE', 'value': '2007-08-09'}}
  - predicted={'kind': 'timex', 'span': [146], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - predicted={'kind': 'timex', 'span': [168], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}

### Doc 82738

- Avg F1: 0.368
- Weak layers: entity, event, timex

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 72 | 6 | 0.040 | 0.333 | 0.071 |
| event | 7 | 51 | 8 | 0.121 | 0.467 | 0.192 |
| timex | 2 | 10 | 5 | 0.167 | 0.286 | 0.211 |
| relation | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.071) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.192) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- timex: low F1 (0.211) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [81, 82], 'attrs': {}} | predicted={'kind': 'entity', 'span': [81, 82, 83], 'attrs': {'syntactic_type': 'NAM'}}
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (71 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [11], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [17], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- boundary_mismatch (3 shown):
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [48], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [60, 61], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumbledown', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [60], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumble', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [83, 84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [83], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [56], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crash', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [56], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crash', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [77], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'NEG', 'pos': 'VERB', 'pred': 'break', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [77], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'break', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- missing (3 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [79], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'record', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (46 shown):
  - predicted={'kind': 'event', 'span': [42], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [59], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [82], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
- timex:
- boundary_mismatch (2 shown):
  - gold={'kind': 'timex', 'span': [7, 8], 'attrs': {'type': 'DATE', 'value': '1987-10-20'}} | predicted={'kind': 'timex', 'span': [8], 'attrs': {'type': 'DATE', 'value': '2007-10-15'}}
  - gold={'kind': 'timex', 'span': [51, 52], 'attrs': {'type': 'DATE', 'value': '1987-10-20'}} | predicted={'kind': 'timex', 'span': [52], 'attrs': {'type': 'DATE', 'value': '2007-10-15'}}
- type_mismatch (3 shown):
  - gold={'kind': 'timex', 'span': [25, 26], 'attrs': {'type': 'DATE', 'value': 'P1D'}} | predicted={'kind': 'timex', 'span': [25, 26], 'attrs': {'type': 'DURATION', 'value': 'P1D'}}
  - gold={'kind': 'timex', 'span': [31, 32, 33], 'attrs': {'type': 'DATE', 'value': 'P20Y'}} | predicted={'kind': 'timex', 'span': [31, 32, 33], 'attrs': {'type': 'DATE', 'value': '1987'}}
  - gold={'kind': 'timex', 'span': [71], 'attrs': {'type': 'DATE', 'value': '2007-10-20'}} | predicted={'kind': 'timex', 'span': [71], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}
- spurious (5 shown):
  - predicted={'kind': 'timex', 'span': [112, 113], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [162, 163], 'attrs': {'type': 'DATE', 'value': '2007-10-18'}}
  - predicted={'kind': 'timex', 'span': [213], 'attrs': {'type': 'DATE', 'value': '2007-10-19'}}

### Doc 96770

- Avg F1: 0.485
- Weak layers: entity, event, timex

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 43 | 12 | 0.173 | 0.429 | 0.247 |
| event | 6 | 19 | 14 | 0.240 | 0.300 | 0.267 |
| timex | 3 | 7 | 1 | 0.300 | 0.750 | 0.429 |
| relation | 13 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.247) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.267) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.429) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [20], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [47, 48, 49, 50], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [48, 49], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [55], 'attrs': {'syntactic_type': 'PRO'}} | predicted={'kind': 'entity', 'span': [55, 56], 'attrs': {'syntactic_type': 'PRO'}}
- type_mismatch (5 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}} | predicted={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [80], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [80], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [82], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [82], 'attrs': {'syntactic_type': 'CONJ'}}
- missing (3 shown):
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [84], 'attrs': {'syntactic_type': 'NAM'}}
- spurious (34 shown):
  - predicted={'kind': 'entity', 'span': [9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [21], 'attrs': {'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [36, 37, 38], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [66], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [66], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'time': 'NON_FUTURE'}}
- missing (12 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (17 shown):
  - predicted={'kind': 'event', 'span': [120], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'market', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [142], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'begin', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- type_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DURATION', 'value': 'PAST_REF'}} | predicted={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
