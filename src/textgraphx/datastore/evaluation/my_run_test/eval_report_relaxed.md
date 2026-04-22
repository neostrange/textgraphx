# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.071 | 0.075 | 0.073 |
| micro | strict | event | 0.193 | 0.099 | 0.131 |
| micro | strict | timex | 0.154 | 0.065 | 0.091 |
| micro | strict | relation | 0.065 | 0.046 | 0.054 |
| micro | relaxed | entity | 0.124 | 0.132 | 0.128 |
| micro | relaxed | event | 0.211 | 0.108 | 0.143 |
| micro | relaxed | timex | 0.154 | 0.065 | 0.091 |
| micro | relaxed | relation | 0.065 | 0.046 | 0.054 |
| macro | strict | entity | 0.012 | 0.078 | 0.021 |
| macro | strict | event | 0.032 | 0.108 | 0.050 |
| macro | strict | timex | 0.026 | 0.083 | 0.039 |
| macro | strict | relation | 0.011 | 0.048 | 0.018 |
| macro | relaxed | entity | 0.021 | 0.137 | 0.036 |
| macro | relaxed | event | 0.035 | 0.118 | 0.054 |
| macro | relaxed | timex | 0.026 | 0.083 | 0.039 |
| macro | relaxed | relation | 0.011 | 0.048 | 0.018 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| has_participant | 0.068 | 0.091 | 0.078 |
| tlink | 0.053 | 0.013 | 0.021 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.131
- Strict TIMEX F1: 0.091
- Strict Relation F1: 0.054
- Composite: 0.096

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.012
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.004

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.128 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- event: micro F1=0.143 below threshold 0.75 - mark as priority optimization track.
- relation: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- relation: micro F1=0.054 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.091 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 112579 | 0.000 | entity, event, timex, relation |
| 61327 | 0.000 | entity, event, timex, relation |
| 62405 | 0.000 | entity, event, timex, relation |
| 82738 | 0.000 | entity, event, timex, relation |
| 96770 | 0.000 | entity, event, timex, relation |
| 76437 | 0.220 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 13 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 23 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
- timex:
- missing (6 shown):
  - gold={'kind': 'timex', 'span': [12, 13, 14, 15], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
  - gold={'kind': 'timex', 'span': [43], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
  - gold={'kind': 'timex', 'span': [74], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (103,), 'entity', (102,), ())
  - gold=('has_participant', 'event', (2,), 'entity', (1,), ())
  - gold=('has_participant', 'event', (26,), 'entity', (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34), ())

### Doc 61327

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 15 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 12 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 16 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plummet', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [22], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'type': 'DATE', 'value': '2007-02-27'}}
  - gold={'kind': 'timex', 'span': [33], 'attrs': {'type': 'DATE', 'value': '2007-02-27'}}
  - gold={'kind': 'timex', 'span': [37], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (22,), 'entity', (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), ())
  - gold=('has_participant', 'event', (3,), 'entity', (1, 2), ())
  - gold=('has_participant', 'event', (41,), 'entity', (43, 44), ())

### Doc 62405

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 31 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (10 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [17], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (6 shown):
  - gold={'kind': 'timex', 'span': [8, 9, 10, 11], 'attrs': {'type': 'DATE', 'value': '2007-03-13'}}
  - gold={'kind': 'timex', 'span': [13, 14], 'attrs': {'type': 'DURATION', 'value': 'P2W'}}
  - gold={'kind': 'timex', 'span': [56], 'attrs': {'type': 'DATE', 'value': '2007-03-12'}}
- relation:
- missing (10 shown):
  - gold=('has_participant', 'event', (104,), 'entity', (107,), ())
  - gold=('has_participant', 'event', (123,), 'entity', (121,), ())
  - gold=('has_participant', 'event', (137,), 'entity', (127, 128, 129, 130, 131, 132, 133, 134, 135), ())

### Doc 76437

- Avg F1: 0.220
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 14 | 99 | 3 | 0.124 | 0.824 | 0.215 |
| event | 12 | 45 | 5 | 0.211 | 0.706 | 0.324 |
| timex | 2 | 11 | 2 | 0.154 | 0.500 | 0.235 |
| relation | 6 | 86 | 15 | 0.065 | 0.286 | 0.106 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.215) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.324) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.106) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.

Top failure examples:
- entity:
- boundary_mismatch (1 shown):
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [69], 'attrs': {'syntactic_type': 'NAM'}}
- missing (2 shown):
  - gold={'kind': 'entity', 'span': [57, 58, 59, 60, 61], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [88, 89, 90], 'attrs': {'syntactic_type': 'NOM'}}
- spurious (10 shown):
  - predicted={'kind': 'entity', 'span': [5, 6], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [19, 20], 'attrs': {'syntactic_type': 'NOM'}}
  - predicted={'kind': 'entity', 'span': [109, 110, 111, 112], 'attrs': {'syntactic_type': 'NAM'}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [102], 'attrs': {'pos': 'NOUN', 'pred': 'tie'}}
- spurious (10 shown):
  - predicted={'kind': 'event', 'span': [113], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'transfer', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [121], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'follow', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [128], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'authorize', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (2 shown):
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [50, 51], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- spurious (10 shown):
  - predicted={'kind': 'timex', 'span': [107], 'attrs': {'type': 'DATE', 'value': '2007-08-09'}}
  - predicted={'kind': 'timex', 'span': [146], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - predicted={'kind': 'timex', 'span': [168], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- endpoint_mismatch (3 shown):
  - gold=('has_participant', 'event', (37,), 'entity', (32, 33, 34, 35, 36), ()) | predicted=('has_participant', 'event', (37,), 'entity', (33, 34, 35, 36), ())
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), ()) | predicted=('has_participant', 'event', (73,), 'entity', (69, 70, 71), ())
  - gold=('has_participant', 'event', (85,), 'entity', (79, 80, 81, 82, 83), ()) | predicted=('has_participant', 'event', (85,), 'entity', (79, 80), ())
- missing (10 shown):
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), ())
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), ())
  - gold=('tlink', 'event', (104,), 'timex', (7, 8, 9, 10), (('reltype', 'AFTER'),))
- spurious (10 shown):
  - predicted=('has_participant', 'event', (113,), 'entity', (118, 119), ())
  - predicted=('has_participant', 'event', (121,), 'entity', (139, 140, 141, 142), ())
  - predicted=('has_participant', 'event', (128,), 'entity', (136, 137), ())

### Doc 82738

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 9 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 15 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 7 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 22 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (9 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [1, 2, 3], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [15], 'attrs': {'syntactic_type': 'HLS'}}
- event:
- missing (10 shown):
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
  - gold=('has_participant', 'event', (16,), 'entity', (15,), ())
  - gold=('has_participant', 'event', (4,), 'entity', (1, 2, 3), ())
  - gold=('has_participant', 'event', (43,), 'entity', (35, 36, 37, 38, 39, 40, 41, 42), ())

### Doc 96770

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 20 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 23 | 0.000 | 0.000 | 0.000 |

Suggested actions:
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: recall is weaker than precision - investigate under-generation and missing extractions.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: recall is weaker than precision - investigate under-generation and missing extractions.
- relation: low F1 (0.000) - inspect extraction and matching rules for this layer.
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- missing (10 shown):
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {}}
  - gold={'kind': 'entity', 'span': [7], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [13], 'attrs': {'syntactic_type': 'PRE.NOM'}}
- event:
- missing (10 shown):
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
  - gold=('has_participant', 'event', (100,), 'entity', (99,), ())
  - gold=('has_participant', 'event', (107,), 'entity', (109, 110, 111), ())
  - gold=('has_participant', 'event', (15,), 'entity', (13, 14), ())
