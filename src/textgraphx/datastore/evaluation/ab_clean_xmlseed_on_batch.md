# Evaluation Report

- Mode: batch
- Documents evaluated: 1
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
| has_participant | 0.000 | 0.000 | 0.000 |
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
| 76437 | 0.000 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 76437

- Avg F1: 0.000
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |
| event | 0 | 0 | 17 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 0 | 0 | 21 | 0.000 | 0.000 | 0.000 |

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
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- event:
- missing (5 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [15], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- missing (5 shown):
  - gold=('has_participant', 'event', (14,), 'entity', (11, 12, 13), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (2, 3), 'entity', (1,), (('sem_role', 'Arg1'),))
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), (('sem_role', 'Argm-LOC'),))
