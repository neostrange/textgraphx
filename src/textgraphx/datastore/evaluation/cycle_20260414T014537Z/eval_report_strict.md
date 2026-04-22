# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.237 | 0.264 | 0.250 |
| micro | strict | event | 0.162 | 0.405 | 0.232 |
| micro | strict | timex | 0.281 | 0.581 | 0.379 |
| micro | strict | relation | 0.154 | 0.031 | 0.051 |
| micro | relaxed | entity | 0.314 | 0.349 | 0.330 |
| micro | relaxed | event | 0.209 | 0.523 | 0.299 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.077 | 0.031 | 0.044 |
| macro | strict | entity | 0.243 | 0.266 | 0.245 |
| macro | strict | event | 0.174 | 0.424 | 0.238 |
| macro | strict | timex | 0.312 | 0.589 | 0.396 |
| macro | strict | relation | 0.106 | 0.030 | 0.045 |
| macro | relaxed | entity | 0.334 | 0.343 | 0.328 |
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

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.250 below threshold 0.75 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.232 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- relation: micro F1=0.051 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- timex: micro F1=0.379 below threshold 0.75 - mark as priority optimization track.
- timex: type mismatch volume present - refine schema mapping and attribute projection.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 82738 | 0.156 | entity, event, timex, relation |
| 76437 | 0.172 | entity, event, timex, relation |
| 61327 | 0.208 | entity, event, timex, relation |
| 96770 | 0.260 | entity, event, timex, relation |
| 112579 | 0.261 | entity, event, timex, relation |
| 62405 | 0.328 | entity, event, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.261
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 14 | 9 | 0.222 | 0.308 | 0.258 |
| event | 8 | 32 | 18 | 0.200 | 0.308 | 0.242 |
| timex | 4 | 10 | 2 | 0.286 | 0.667 | 0.400 |
| relation | 2 | 3 | 21 | 0.400 | 0.087 | 0.143 |

Suggested actions:
- entity: low F1 (0.258) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.242) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.143) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.400) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- missing (9 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
- spurious (14 shown):
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
- spurious (29 shown):
  - predicted={'kind': 'event', 'span': [150], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'shed', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [167], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'investment', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [183], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'post', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
- missing (21 shown):
  - gold=('has_participant', 'event', (103,), 'entity', (102,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (2,), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), (('sem_role', 'Arg1'),))
- spurious (3 shown):
  - predicted=('tlink', 'event', (28,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (30,), 'timex', (43,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (69,), 'timex', (74,), (('reltype', 'IS_INCLUDED'),))

### Doc 61327

- Avg F1: 0.208
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 12 | 12 | 0.200 | 0.200 | 0.200 |
| event | 6 | 22 | 6 | 0.214 | 0.500 | 0.300 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.200) - inspect extraction and matching rules for this layer.
- event: low F1 (0.300) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}} | predicted={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [69, 70], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [70], 'attrs': {'syntactic_type': 'NAM'}}
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14, 15], 'attrs': {}}
- spurious (10 shown):
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
- missing (16 shown):
  - gold=('has_participant', 'event', (22,), 'entity', (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (3,), 'entity', (1, 2), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), (('sem_role', 'Arg1'),))

### Doc 62405

- Avg F1: 0.328
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 9 | 13 | 22 | 0.409 | 0.290 | 0.340 |
| event | 9 | 59 | 12 | 0.132 | 0.429 | 0.202 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.340) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.202) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (22 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (13 shown):
  - predicted={'kind': 'entity', 'span': [171, 172], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [176, 177], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179, 180], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [84], 'attrs': {}} | predicted={'kind': 'event', 'span': [84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
- missing (26 shown):
  - gold=('has_participant', 'event', (104,), 'entity', (107,), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (123,), 'entity', (121,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (137,), 'entity', (127, 128, 129, 130, 131, 132, 133, 134, 135), (('sem_role', 'Arg0'),))

### Doc 76437

- Avg F1: 0.172
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 25 | 14 | 0.107 | 0.176 | 0.133 |
| event | 10 | 49 | 7 | 0.169 | 0.588 | 0.263 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 1 | 14 | 20 | 0.067 | 0.048 | 0.056 |

Suggested actions:
- entity: low F1 (0.133) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.263) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.056) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- missing (14 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (25 shown):
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [122, 123, 124, 125], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [149], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- boundary_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [95], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [95], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fear', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
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
- missing (20 shown):
  - gold=('has_participant', 'event', (14,), 'entity', (11, 12, 13), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
- spurious (14 shown):
  - predicted=('tlink', 'event', (113,), 'timex', (107,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (128,), 'timex', (107,), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (134,), 'timex', (107,), (('reltype', 'IS_INCLUDED'),))

### Doc 82738

- Avg F1: 0.156
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 3 | 15 | 6 | 0.167 | 0.333 | 0.222 |
| event | 7 | 51 | 8 | 0.121 | 0.467 | 0.192 |
| timex | 2 | 10 | 5 | 0.167 | 0.286 | 0.211 |
| relation | 0 | 0 | 22 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.222) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.192) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
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
- spurious (15 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [51, 52], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [105], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- boundary_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [60, 61], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumbledown', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [60], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumble', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [83, 84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [83], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [56], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crash', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [56], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crash', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [77], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'NEG', 'pos': 'VERB', 'pred': 'break', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [77], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'break', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- missing (4 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- spurious (47 shown):
  - predicted={'kind': 'event', 'span': [47], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'be', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [98], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'blame', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [101], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'loss', 'time': 'NON_FUTURE'}}
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
- missing (22 shown):
  - gold=('has_participant', 'event', (16,), 'entity', (15,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (4,), 'entity', (1, 2, 3), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (43,), 'entity', (35, 36, 37, 38, 39, 40, 41, 42), (('sem_role', 'Arg1'),))

### Doc 96770

- Avg F1: 0.260
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 11 | 15 | 0.353 | 0.286 | 0.316 |
| event | 5 | 19 | 15 | 0.208 | 0.250 | 0.227 |
| timex | 3 | 7 | 1 | 0.300 | 0.750 | 0.429 |
| relation | 1 | 5 | 22 | 0.167 | 0.043 | 0.069 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.316) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.227) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.069) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.429) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (3 shown):
  - gold={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [20], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [47, 48, 49, 50], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [48, 49], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [80], 'attrs': {'syntactic_type': 'CONJ'}}
- type_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [82], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [82], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [84], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [84], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [86], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [86], 'attrs': {'syntactic_type': 'CONJ'}}
- missing (8 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [13, 14], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (4 shown):
  - predicted={'kind': 'entity', 'span': [113, 114, 115], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [134], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [179], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [66], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [66], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attack', 'time': 'NON_FUTURE'}}
- missing (13 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (17 shown):
  - predicted={'kind': 'event', 'span': [75], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'be', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [129], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'have', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
- timex:
- type_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DURATION', 'value': 'PAST_REF'}} | predicted={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- missing (22 shown):
  - gold=('has_participant', 'event', (100,), 'entity', (99,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (107,), 'entity', (109, 110, 111), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (15,), 'entity', (13, 14), (('sem_role', 'Arg1'),))
- spurious (5 shown):
  - predicted=('tlink', 'event', (180,), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (188,), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
  - predicted=('tlink', 'event', (191,), 'timex', (175, 176), (('reltype', 'IS_INCLUDED'),))
