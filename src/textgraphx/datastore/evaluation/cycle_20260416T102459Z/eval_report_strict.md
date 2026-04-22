# Evaluation Report

- Mode: batch
- Documents evaluated: 6
- Skipped files (missing predictions): 0

## Aggregate Metrics

| Scope | Mode | Layer | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| micro | strict | entity | 0.000 | 0.000 | 0.000 |
| micro | strict | event | 0.000 | 0.000 | 0.000 |
| micro | strict | timex | 0.000 | 0.000 | 0.000 |
| micro | strict | relation | 0.000 | 0.000 | 0.000 |
| micro | relaxed | entity | 0.000 | 0.000 | 0.000 |
| micro | relaxed | event | 0.000 | 0.000 | 0.000 |
| micro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| micro | relaxed | relation | 0.000 | 0.000 | 0.000 |
| macro | strict | entity | 0.000 | 0.000 | 0.000 |
| macro | strict | event | 0.000 | 0.000 | 0.000 |
| macro | strict | timex | 0.000 | 0.000 | 0.000 |
| macro | strict | relation | 0.000 | 0.000 | 0.000 |
| macro | relaxed | entity | 0.000 | 0.000 | 0.000 |
| macro | relaxed | event | 0.000 | 0.000 | 0.000 |
| macro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| macro | relaxed | relation | 0.000 | 0.000 | 0.000 |

## Relation Kind Breakdown (Micro Strict)

| Relation Kind | Precision | Recall | F1 |
|---|---:|---:|---:|
| tlink | 0.000 | 0.000 | 0.000 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.000
- Strict TIMEX F1: 0.000
- Strict Relation F1: 0.000
- Composite: 0.000

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.000
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.000

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- entity: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- event: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- event: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- relation: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- relation: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.000 below threshold 0.75 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 112579 | 0.000 | entity, event, timex, relation |
| 61327 | 0.000 | entity, event, timex, relation |
| 62405 | 0.000 | entity, event, timex, relation |
| 76437 | 0.000 | entity, event, timex, relation |
| 82738 | 0.000 | entity, event, timex, relation |
| 96770 | 0.000 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 112579

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 13 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 26 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 14 | 0.000 | 0.000 | 0.000 |

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
- missing (13 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34], 'attrs': {'syntactic_type': 'APP'}}
- event:
- missing (26 shown):
  - gold={'kind': 'event', 'span': [2], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [11], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'news', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [26], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'use', 'tense': 'PASTPART', 'time': 'NON_FUTURE'}}
- timex:
- missing (6 shown):
  - gold={'kind': 'timex', 'span': [12, 13, 14, 15], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
  - gold={'kind': 'timex', 'span': [43], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
  - gold={'kind': 'timex', 'span': [74], 'attrs': {'type': 'DATE', 'value': '2008-09-04'}}
- relation:
- missing (14 shown):
  - gold=('tlink', 'event', (103,), 'timex', (104,), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (107,), 'timex', (109, 110), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (107,), 'timex', (12, 13, 14, 15), (('reltype', 'BEFORE'),))

### Doc 61327

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 15 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 12 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 11 | 0.000 | 0.000 | 0.000 |

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
- missing (15 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13, 14, 15, 16], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (12 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plummet', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [22], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'plunge', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'type': 'DATE', 'value': '2007-02-27'}}
  - gold={'kind': 'timex', 'span': [33], 'attrs': {'type': 'DATE', 'value': '2007-02-27'}}
  - gold={'kind': 'timex', 'span': [37], 'attrs': {'type': 'DATE', 'value': 'P1D'}}
- relation:
- missing (11 shown):
  - gold=('tlink', 'event', (22,), 'event', (76,), (('reltype', 'SIMULTANEOUS'),))
  - gold=('tlink', 'event', (22,), 'timex', (33,), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (22,), 'timex', (7, 8, 9, 10), (('reltype', 'IS_INCLUDED'),))

### Doc 62405

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 31 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 6 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 12 | 0.000 | 0.000 | 0.000 |

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
- missing (31 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'PRE.NOM'}}
  - gold={'kind': 'entity', 'span': [1, 2], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [6, 7], 'attrs': {'syntactic_type': 'NOM'}}
- event:
- missing (21 shown):
  - gold={'kind': 'event', 'span': [3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PRESENT', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [4], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'jitters', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [17], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'send', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (6 shown):
  - gold={'kind': 'timex', 'span': [8, 9, 10, 11], 'attrs': {'type': 'DATE', 'value': '2007-03-13'}}
  - gold={'kind': 'timex', 'span': [13, 14], 'attrs': {'type': 'DURATION', 'value': 'P2W'}}
  - gold={'kind': 'timex', 'span': [56], 'attrs': {'type': 'DATE', 'value': '2007-03-12'}}
- relation:
- missing (12 shown):
  - gold=('tlink', 'event', (109,), 'timex', (111, 112, 113), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (17,), 'event', (35,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (17,), 'event', (52,), (('reltype', 'BEFORE'),))

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
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
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
- missing (11 shown):
  - gold=('tlink', 'event', (104,), 'timex', (7, 8, 9, 10), (('reltype', 'AFTER'),))
  - gold=('tlink', 'event', (14,), 'event', (37,), (('reltype', 'BEFORE'),))
  - gold=('tlink', 'event', (14,), 'timex', (15,), (('reltype', 'IS_INCLUDED'),))

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
- missing (15 shown):
  - gold=('tlink', 'event', (16,), 'timex', (11, 12, 13, 14), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (24,), 'event', (43,), (('reltype', 'BEGUN_BY'),))
  - gold=('tlink', 'event', (24,), 'timex', (11, 12, 13, 14), (('reltype', 'SIMULTANEOUS'),))

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
- relation: recall is weaker than precision - investigate under-generation and missing extractions.
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
- missing (13 shown):
  - gold=('tlink', 'event', (100,), 'timex', (9, 10, 11, 12), (('reltype', 'IS_INCLUDED'),))
  - gold=('tlink', 'event', (15,), 'event', (51,), (('reltype', 'INCLUDES'),))
  - gold=('tlink', 'event', (15,), 'timex', (21,), (('reltype', 'IS_INCLUDED'),))
