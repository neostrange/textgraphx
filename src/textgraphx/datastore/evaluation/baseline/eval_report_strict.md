# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.272 | 0.349 | 0.306 |
| micro | strict | event | 0.166 | 0.414 | 0.237 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 0.078 | 0.145 | 0.101 |
| micro | relaxed | entity | 0.301 | 0.398 | 0.343 |
| micro | relaxed | event | 0.217 | 0.541 | 0.309 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.039 | 0.145 | 0.061 |
| macro | strict | entity | 0.283 | 0.350 | 0.304 |
| macro | strict | event | 0.171 | 0.431 | 0.238 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 0.081 | 0.147 | 0.100 |
| macro | relaxed | entity | 0.315 | 0.406 | 0.346 |
| macro | relaxed | event | 0.223 | 0.564 | 0.310 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.040 | 0.147 | 0.061 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| tlink | 0.078 | 0.145 | 0.101 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.237
- Strict TIMEX F1: 0.379
- Strict Relation F1: 0.101
- Composite: 0.239

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
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.306 below threshold 0.75 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.237 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.101 below threshold 0.75 - mark as priority optimization track.
- relation: type mismatch volume present - refine schema mapping and attribute projection.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- timex: micro F1=0.379 below threshold 0.75 - mark as priority optimization track.
- timex: type mismatch volume present - refine schema mapping and attribute projection.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.187 | entity, event, timex, relation |
| 82738 | 0.187 | entity, event, timex, relation |
| 61327 | 0.226 | entity, event, timex, relation |
| 112579 | 0.262 | entity, event, timex, relation |
| 96770 | 0.326 | entity, event, timex, relation |
| 62405 | 0.367 | entity, event, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.262
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 17 | 7 | 0.261 | 0.462 | 0.333 |
| event | 8 | 41 | 18 | 0.163 | 0.308 | 0.213 |
| timex | 4 | 10 | 2 | 0.286 | 0.667 | 0.400 |
| relation | 2 | 23 | 12 | 0.080 | 0.143 | 0.103 |

Suggested actions:
- entity: low F1 (0.333) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.213) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.103) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.400) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- missing (7 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (17 shown):
  - predicted={'kind': 'entity', 'span': [160, 161], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [166, 167], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [174, 175, 176, 177], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (3 shown):
  - gold={'kind': 'event', 'span': [30], 'attrs': {'aspect': 'NONE', 'pos': 'NOUN', 'pred': 'performance', 'tense': 'NONE'}} | predicted={'kind': 'event', 'span': [30], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'performance', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [69], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [69], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [86], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sale', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [86], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sale', 'time': 'NON_FUTURE'}}
- missing (15 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (38 shown):
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
- relation:
- missing (12 shown):
  - gold=('tlink', 'event', (103,), 'timex', (104,), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (107,), 'timex', (12, 13, 14, 15), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (36,), 'event', (40,), (('reltype', 'IS_INCLUDED'),))
- spurious (23 shown):
  - predicted=('tlink', 'event', (183,), 'event', (211,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (183,), 'event', (223,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (183,), 'event', (239,), (('reltype', 'BEFORE'),))

### Doc 61327

- Avg F1: 0.226
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 14 | 11 | 0.222 | 0.267 | 0.242 |
| event | 6 | 28 | 6 | 0.176 | 0.500 | 0.261 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 1 | 17 | 10 | 0.056 | 0.091 | 0.069 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.242) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.261) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.069) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [69, 70], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [70], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72, 73, 74], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [72, 73], 'attrs': {'syntactic_type': 'NAM'}}
- missing (9 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
- spurious (12 shown):
  - predicted={'kind': 'entity', 'span': [110], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [157, 158], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attacks', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'time': 'NON_FUTURE'}}
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
  - gold=('tlink', 'event', (22,), 'event', (76,), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (22,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (38,), 'event', (41,), (('reltype', 'AFTER'),))
- spurious (17 shown):
  - predicted=('tlink', 'event', (159,), 'event', (255,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (168,), 'timex', (161,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (177,), 'timex', (161,), (('reltype', 'IS_INCLUDED'),))

### Doc 62405

- Avg F1: 0.367
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 16 | 22 | 0.360 | 0.290 | 0.321 |
| event | 10 | 48 | 11 | 0.172 | 0.476 | 0.253 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 2 | 18 | 10 | 0.100 | 0.167 | 0.125 |

Suggested actions:
- entity: low F1 (0.321) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.253) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.125) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (22 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (16 shown):
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [176, 177], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179, 180], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [84], 'attrs': {}} | predicted={'kind': 'event', 'span': [84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
- endpoint_mismatch (1 shown):
  - gold=('tlink', 'event', (84, 85), 'event', (96,), (('reltype', 'AFTER'),)) | predicted=('tlink', 'event', (84,), 'event', (96,), (('reltype', 'BEFORE'),))
- missing (9 shown):
  - gold=('tlink', 'event', (17,), 'event', (35,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (17,), 'event', (52,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (17,), 'timex', (8, 9, 10, 11), (('reltype', 'BEFORE'),))
- spurious (17 shown):
  - predicted=('tlink', 'event', (104,), 'timex', (111, 112, 113), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (109,), 'timex', (13, 14), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (165,), 'event', (188,), (('reltype', 'AFTER'),))

### Doc 76437

- Avg F1: 0.187
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 28 | 14 | 0.097 | 0.176 | 0.125 |
| event | 10 | 45 | 7 | 0.182 | 0.588 | 0.278 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 3 | 41 | 8 | 0.068 | 0.273 | 0.109 |

Suggested actions:
- entity: low F1 (0.125) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.278) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.109) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- type_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {}} | predicted={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {'syntactic_type': 'NAM'}}
- missing (13 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (27 shown):
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [142], 'attrs': {'syntactic_type': 'APP'}}
- event:
- boundary_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [95], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [95], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
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
- type_mismatch (1 shown):
  - gold=('tlink', 'event', (37,), 'event', (62,), (('reltype', 'AFTER'),)) | predicted=('tlink', 'event', (37,), 'event', (62,), (('reltype', 'BEFORE'),))
- missing (7 shown):
  - gold=('tlink', 'event', (104,), 'timex', (7, 8, 9, 10), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (37,), 'event', (43,), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (37,), 'timex', (38, 39, 40, 41), (('reltype', 'IS_INCLUDED'),))
- spurious (40 shown):
  - predicted=('tlink', 'event', (113,), 'event', (150,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (113,), 'event', (174,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (113,), 'event', (187,), (('reltype', 'BEFORE'),))

### Doc 82738

- Avg F1: 0.187
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 16 | 6 | 0.158 | 0.333 | 0.214 |
| event | 7 | 50 | 8 | 0.123 | 0.467 | 0.194 |
| timex | 2 | 10 | 5 | 0.167 | 0.286 | 0.211 |
| relation | 2 | 14 | 13 | 0.125 | 0.133 | 0.129 |

Suggested actions:
- entity: low F1 (0.214) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.194) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.129) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- timex: low F1 (0.211) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- missing (6 shown):
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}}
- spurious (16 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [51, 52], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [105], 'attrs': {'syntactic_type': 'NAM'}}
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
- spurious (45 shown):
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
- relation:
- missing (13 shown):
  - gold=('tlink', 'event', (16,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (24,), 'event', (43,), (('reltype', 'BEGUN_BY'),))
  - gold=('tlink', 'event', (24,), 'timex', (11, 12, 13, 14), (('reltype', 'SIMULTANEOUS'),))
- spurious (14 shown):
  - predicted=('tlink', 'event', (122,), 'event', (124,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (137,), 'event', (174,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (174,), 'event', (216,), (('reltype', 'AFTER'),))

### Doc 96770

- Avg F1: 0.326
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 12 | 8 | 9 | 0.600 | 0.571 | 0.585 |
| event | 5 | 19 | 15 | 0.208 | 0.250 | 0.227 |
| timex | 3 | 7 | 1 | 0.300 | 0.750 | 0.429 |
| relation | 1 | 17 | 12 | 0.056 | 0.077 | 0.065 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.585) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.227) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.065) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: type mismatches detected - tune label/attribute mapping in mapping-config.
- timex: low F1 (0.429) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [47, 48, 49, 50], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [48, 49], 'attrs': {'syntactic_type': 'NAM'}}
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (7 shown):
  - predicted={'kind': 'entity', 'span': [36, 37, 38], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [134], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [66], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [66], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'time': 'NON_FUTURE'}}
- missing (13 shown):
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
- relation:
- type_mismatch (3 shown):
  - gold=('tlink', 'event', (15,), 'event', (51,), (('reltype', 'INCLUDES'),)) | predicted=('tlink', 'event', (15,), 'event', (51,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (51,), 'event', (76,), (('reltype', 'IS_INCLUDED'),)) | predicted=('tlink', 'event', (51,), 'event', (76,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (76,), 'event', (100,), (('reltype', 'BEGUN_BY'),)) | predicted=('tlink', 'event', (76,), 'event', (100,), (('reltype', 'BEFORE'),))
- missing (9 shown):
  - gold=('tlink', 'event', (100,), 'timex', (9, 10, 11, 12), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (15,), 'timex', (9, 10, 11, 12), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (38,), 'timex', (40, 41), (('reltype', 'IS_INCLUDED'),))
- spurious (14 shown):
  - predicted=('tlink', 'event', (130,), 'event', (142,), (('reltype', 'AFTER'),))
  - predicted=('tlink', 'event', (142,), 'event', (180,), (('reltype', 'BEFORE'),))
  - predicted=('tlink', 'event', (142,), 'event', (229,), (('reltype', 'BEFORE'),))
