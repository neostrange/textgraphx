# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.115 | 0.387 | 0.178 |
| micro | strict | event | 0.082 | 0.207 | 0.118 |
| micro | strict | timex | 0.266 | 0.548 | 0.358 |
| micro | strict | relation | 0.054 | 0.122 | 0.075 |
| micro | relaxed | entity | 0.172 | 0.575 | 0.265 |
| micro | relaxed | event | 0.214 | 0.541 | 0.307 |
| micro | relaxed | timex | 0.391 | 0.806 | 0.526 |
| micro | relaxed | relation | 0.055 | 0.122 | 0.075 |
| macro | strict | entity | 0.127 | 0.402 | 0.187 |
| macro | strict | event | 0.088 | 0.208 | 0.120 |
| macro | strict | timex | 0.300 | 0.562 | 0.379 |
| macro | strict | relation | 0.058 | 0.121 | 0.076 |
| macro | relaxed | entity | 0.186 | 0.611 | 0.275 |
| macro | relaxed | event | 0.222 | 0.568 | 0.309 |
| macro | relaxed | timex | 0.410 | 0.778 | 0.524 |
| macro | relaxed | relation | 0.059 | 0.121 | 0.076 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.046 | 0.218 | 0.076 |
| tlink | 0.121 | 0.053 | 0.073 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.118
- Strict TIMEX F1: 0.358
- Strict Relation F1: 0.075
- Composite: 0.177

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.189
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.057

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.178 below threshold 0.75 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.118 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.075 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- timex: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- timex: micro F1=0.358 below threshold 0.75 - mark as priority optimization track.
- timex: type mismatch volume present - refine schema mapping and attribute projection.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 82738 | 0.109 | entity, event, timex, relation |
| 76437 | 0.137 | entity, event, timex, relation |
| 61327 | 0.182 | entity, event, timex, relation |
| 112579 | 0.194 | entity, event, timex, relation |
| 96770 | 0.248 | entity, event, timex, relation |
| 62405 | 0.272 | entity, event, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.194
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 7 | 48 | 6 | 0.127 | 0.538 | 0.206 |
| event | 7 | 44 | 19 | 0.137 | 0.269 | 0.182 |
| timex | 3 | 11 | 3 | 0.214 | 0.500 | 0.300 |
| relation | 3 | 42 | 20 | 0.067 | 0.130 | 0.088 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.206) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.182) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.088) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- timex: low F1 (0.300) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}} | predicted={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [102], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [102, 103, 104, 105, 106], 'attrs': {'syntactic_type': 'NOM'}}
- missing (4 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [32], 'attrs': {'syntactic_type': 'PRE.NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [12], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [60, 61], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [74, 75], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- boundary_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [86], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sale', 'tense': 'NONE', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [85, 86], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sale', 'time': 'NON_FUTURE'}}
- type_mismatch (2 shown):
  - gold={'kind': 'event', 'span': [30], 'attrs': {'aspect': 'NONE', 'pos': 'NOUN', 'pred': 'performance', 'tense': 'NONE'}} | predicted={'kind': 'event', 'span': [30], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'performance', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [69], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [69], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'time': 'NON_FUTURE'}}
- missing (10 shown):
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [40], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [32, 33, 34], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'exchange', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [93], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [116], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'accord', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- timex:
- boundary_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [12, 13, 14, 15], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}} | predicted={'kind': 'timex', 'span': [12, 14, 15], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
- type_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [125], 'attrs': {'type': 'DURATION', 'value': 'PY5'}} | predicted={'kind': 'timex', 'span': [125], 'attrs': {'type': 'DURATION', 'value': 'P5Y'}}
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [104], 'attrs': {'type': 'SET', 'value': 'P1W'}}
- spurious (9 shown):
  - predicted={'kind': 'timex', 'span': [277], 'attrs': {'type': 'DATE', 'value': '2008-09-03'}}
  - predicted={'kind': 'timex', 'span': [292], 'attrs': {'type': 'DATE', 'value': '2008-06'}}
  - predicted={'kind': 'timex', 'span': [294, 295], 'attrs': {'type': 'DATE', 'value': '2008'}}
- relation:
- endpoint_mismatch (2 shown):
  - gold=('has_participant', 'event', (103,), 'entity', (102,), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (103,), 'entity', (102, 103, 104, 105, 106), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (36,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (36,), 'entity', (16, 17, 18, 19, 20), (('sem_role', 'Arg1'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (2,), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (30,), 'entity', (32, 33, 34), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (103,), 'entity', (102, 103, 104, 105, 106), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (134,), 'entity', (132, 133, 134), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (136,), 'entity', (132, 133, 134), (('sem_role', 'Arg0'),))

### Doc 61327

- Avg F1: 0.182
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 6 | 34 | 9 | 0.150 | 0.400 | 0.218 |
| event | 3 | 31 | 9 | 0.088 | 0.250 | 0.130 |
| timex | 2 | 6 | 2 | 0.250 | 0.500 | 0.333 |
| relation | 1 | 25 | 15 | 0.038 | 0.062 | 0.048 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.218) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.130) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.048) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.333) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'APP'}} | predicted={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'APP'}}
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72, 73, 74], 'attrs': {'syntactic_type': 'CONJ'}} | predicted={'kind': 'entity', 'span': [70], 'attrs': {'syntactic_type': 'NAM'}}
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [13, 14, 15], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [43, 44], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [86, 87], 'attrs': {'syntactic_type': 'PRO'}}
  - predicted={'kind': 'entity', 'span': [97], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- type_mismatch (4 shown):
  - gold={'kind': 'event', 'span': [38], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'decline', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [38], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'plunge', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'attacks', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [50], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'plunge', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [53], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'slip', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [53], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'follow', 'time': 'NON_FUTURE'}}
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [41], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'open', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [58], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [44], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'plunge', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [45], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
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
- endpoint_mismatch (1 shown):
  - gold=('has_participant', 'event', (22,), 'entity', (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (22,), 'entity', (12, 13, 14, 15, 16), (('sem_role', 'Arg1'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (58,), 'entity', (60, 61), (('sem_role', 'Argm-OTHER'),))
  - gold=('has_participant', 'event', (76,), 'entity', (63, 64, 65), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (116,), 'entity', (112, 113, 114), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (141,), 'entity', (139,), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (151,), 'entity', (148, 149), (('sem_role', 'Arg0'),))

### Doc 62405

- Avg F1: 0.272
- Weak layers: entity, event, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 11 | 68 | 20 | 0.139 | 0.355 | 0.200 |
| event | 3 | 57 | 18 | 0.050 | 0.143 | 0.074 |
| timex | 5 | 2 | 1 | 0.714 | 0.833 | 0.769 |
| relation | 2 | 59 | 24 | 0.033 | 0.077 | 0.046 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.200) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.074) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.046) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [27, 28], 'attrs': {'syntactic_type': 'PRE.NOM'}} | predicted={'kind': 'entity', 'span': [27, 28, 29], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [44, 45, 46, 47, 48, 49, 50], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [45, 46, 47, 48, 49, 50], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [68, 69, 70, 71], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [68, 69, 70], 'attrs': {'syntactic_type': 'NAM'}}
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [27, 28, 29, 30, 31, 32, 33], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [4], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [8], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [22], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- boundary_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [99, 104], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [104], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'rise', 'time': 'NON_FUTURE'}}
- type_mismatch (6 shown):
  - gold={'kind': 'event', 'span': [17], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [17], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PAST', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [22], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'tumble', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [22], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'send', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [61], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'mark', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [61], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- missing (10 shown):
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'grow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [25], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'worry', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [39], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'send', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [50], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [147], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PRESENT', 'time': 'FUTURE'}}
- timex:
- missing (1 shown):
  - gold={'kind': 'timex', 'span': [119], 'attrs': {'type': 'DURATION', 'value': 'PXY'}}
- spurious (2 shown):
  - predicted={'kind': 'timex', 'span': [217], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
  - predicted={'kind': 'timex', 'span': [411], 'attrs': {'type': 'DATE', 'value': 'PRESENT_REF'}}
- relation:
- endpoint_mismatch (3 shown):
  - gold=('has_participant', 'event', (35,), 'entity', (27, 28, 29, 30, 31, 32, 33), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (35,), 'entity', (27, 28, 29), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (52,), 'entity', (44, 45, 46, 47, 48, 49, 50), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (52,), 'entity', (45, 46, 47, 48, 49, 50), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (84, 85), 'entity', (68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (84,), 'entity', (68, 69, 70), (('sem_role', 'Arg1'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (104,), 'entity', (107,), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (123,), 'entity', (121,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (137,), 'entity', (127, 128, 129, 130, 131, 132, 133, 134, 135), (('sem_role', 'Arg0'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (109,), 'entity', (107, 108), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (147,), 'entity', (142, 143, 144, 145), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (147,), 'entity', (150,), (('sem_role', 'Arg1'),))

### Doc 76437

- Avg F1: 0.137
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 5 | 81 | 12 | 0.058 | 0.294 | 0.097 |
| event | 4 | 49 | 13 | 0.075 | 0.235 | 0.114 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 5 | 73 | 16 | 0.064 | 0.238 | 0.101 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.097) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.114) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.101) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (4 shown):
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}} | predicted={'kind': 'entity', 'span': [24, 25, 26], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [69, 70, 71], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [79, 80, 81, 82, 83], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [79, 80], 'attrs': {'syntactic_type': 'NOM'}}
- type_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {}} | predicted={'kind': 'entity', 'span': [32, 33, 34, 35, 36], 'attrs': {'syntactic_type': 'NAM'}}
- missing (7 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [57, 58, 59, 60, 61], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [82, 83], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [5, 6], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- boundary_mismatch (1 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (7 shown):
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [21], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'stem', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [21], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [26], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fall', 'time': 'NON_FUTURE'}}
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [121], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
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
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (73,), 'entity', (69, 70, 71), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (85,), 'entity', (79, 80, 81, 82, 83), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (85,), 'entity', (79, 80), (('sem_role', 'Arg0'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), (('sem_role', 'Arg1'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (113,), 'entity', (118, 119), (('sem_role', 'Arg2'),))
  - predicted=('has_participant', 'event', (121,), 'entity', (139, 140, 141, 142), (('sem_role', 'Arg2'),))
  - predicted=('has_participant', 'event', (128,), 'entity', (136, 137), (('sem_role', 'Arg1'),))

### Doc 82738

- Avg F1: 0.109
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 4 | 55 | 5 | 0.068 | 0.444 | 0.118 |
| event | 3 | 55 | 12 | 0.052 | 0.200 | 0.082 |
| timex | 2 | 10 | 5 | 0.167 | 0.286 | 0.211 |
| relation | 1 | 52 | 21 | 0.019 | 0.045 | 0.027 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.118) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- event: low F1 (0.082) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.027) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- timex: low F1 (0.211) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (3 shown):
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41], 'attrs': {}} | predicted={'kind': 'entity', 'span': [36, 37, 38, 39, 40, 41, 42], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [58, 59], 'attrs': {'syntactic_type': 'NOM'}} | predicted={'kind': 'entity', 'span': [59], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [81, 82], 'attrs': {}} | predicted={'kind': 'entity', 'span': [81, 82, 83], 'attrs': {'syntactic_type': 'NAM'}}
- missing (2 shown):
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
  - gold={'kind': 'entity', 'span': [35, 36, 37, 38, 39, 40, 41, 42], 'attrs': {'syntactic_type': 'NAM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [11], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [17], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- boundary_mismatch (3 shown):
  - gold={'kind': 'event', 'span': [48, 49], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'know', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [48], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'mark', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [60, 61], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tumbledown', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [60], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [83, 84], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'close', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [83], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'break', 'tense': 'PAST', 'time': 'FUTURE'}}
- type_mismatch (7 shown):
  - gold={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [16], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [18], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tend', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [18], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'say', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'repeat', 'tense': 'INFINITIVE', 'time': 'FUTURE'}} | predicted={'kind': 'event', 'span': [20], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'tend', 'tense': 'INFINITIVE', 'time': 'NON_FUTURE'}}
- missing (2 shown):
  - gold={'kind': 'event', 'span': [10], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'anniversary', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [79], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'record', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [42], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crash', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [59], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'send', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [82], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'close', 'time': 'NON_FUTURE'}}
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
- endpoint_mismatch (4 shown):
  - gold=('has_participant', 'event', (43,), 'entity', (35, 36, 37, 38, 39, 40, 41, 42), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (43,), 'entity', (36, 37, 38, 39, 40, 41, 42), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (60, 61), 'entity', (58, 59), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (60,), 'entity', (59,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (65,), 'entity', (58, 59), (('sem_role', 'Arg0'),)) | predicted=('has_participant', 'event', (65,), 'entity', (59,), (('sem_role', 'Arg1'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (16,), 'entity', (15,), (('sem_role', 'Arg0'),))
  - gold=('has_participant', 'event', (77,), 'entity', (73, 74, 75), (('sem_role', 'Arg0'),))
  - gold=('tlink', 'event', (16,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (124,), 'entity', (126,), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (137,), 'entity', (136,), (('sem_role', 'Arg0'),))
  - predicted=('has_participant', 'event', (137,), 'entity', (138, 139), (('sem_role', 'Arg1'),))

### Doc 96770

- Avg F1: 0.248
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 8 | 28 | 13 | 0.222 | 0.381 | 0.281 |
| event | 3 | 21 | 17 | 0.125 | 0.150 | 0.136 |
| timex | 3 | 7 | 1 | 0.300 | 0.750 | 0.429 |
| relation | 4 | 27 | 19 | 0.129 | 0.174 | 0.148 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.281) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.136) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.148) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.429) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: type mismatches detected - tune label/attribute mapping in mapping-config.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [47, 48, 49, 50], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [48, 49], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [55], 'attrs': {'syntactic_type': 'PRO'}} | predicted={'kind': 'entity', 'span': [55, 56], 'attrs': {'syntactic_type': 'PRO'}}
- type_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}} | predicted={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [18, 19, 20], 'attrs': {'syntactic_type': 'CONJ'}}
  - gold={'kind': 'entity', 'span': [20], 'attrs': {'syntactic_type': 'NAM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [9], 'attrs': {'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [26, 27], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [48, 49, 50], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- type_mismatch (4 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [15], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drop', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [15], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drop', 'tense': 'PAST', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [32], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'cause', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [32], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drop', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- missing (10 shown):
  - gold={'kind': 'event', 'span': [5], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [8], 'attrs': {'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'recession', 'time': 'FUTURE'}}
  - gold={'kind': 'event', 'span': [24], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'fear', 'tense': 'NONE', 'time': 'NON_FUTURE'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [120], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'be', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [130], 'attrs': {'aspect': 'PERFECTIVE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'buy', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [142], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'spread', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- type_mismatch (1 shown):
  - gold={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DURATION', 'value': 'PAST_REF'}} | predicted={'kind': 'timex', 'span': [101], 'attrs': {'type': 'DATE', 'value': 'PAST_REF'}}
- spurious (6 shown):
  - predicted={'kind': 'timex', 'span': [60, 61, 62, 63], 'attrs': {'type': 'DATE', 'value': '2001-09-11'}}
  - predicted={'kind': 'timex', 'span': [150, 151], 'attrs': {'type': 'DATE', 'value': '2007'}}
  - predicted={'kind': 'timex', 'span': [175, 176], 'attrs': {'type': 'DATE', 'value': '2008-W03'}}
- relation:
- endpoint_mismatch (1 shown):
  - gold=('has_participant', 'event', (51,), 'entity', (47, 48, 49, 50), (('sem_role', 'Arg1'),)) | predicted=('has_participant', 'event', (51,), 'entity', (48, 49, 50), (('sem_role', 'Arg1'),))
- missing (10 shown):
  - gold=('has_participant', 'event', (107,), 'entity', (109, 110, 111), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (15,), 'entity', (18, 19, 20), (('sem_role', 'Argm-LOC'),))
  - gold=('has_participant', 'event', (24,), 'entity', (29, 30, 31), (('sem_role', 'Argm-LOC'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (100,), 'entity', (101, 102), (('sem_role', 'Arg2'),))
  - predicted=('has_participant', 'event', (100,), 'entity', (107,), (('sem_role', 'Arg1'),))
  - predicted=('has_participant', 'event', (130,), 'entity', (126, 127), (('sem_role', 'Arg0'),))
