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
| micro | strict | relation | 0.073 | 0.333 | 0.120 |
| micro | relaxed | entity | 0.064 | 0.176 | 0.094 |
| micro | relaxed | event | 0.169 | 0.824 | 0.280 |
| micro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| micro | relaxed | relation | 0.073 | 0.333 | 0.120 |
| macro | strict | entity | 0.000 | 0.000 | 0.000 |
| macro | strict | event | 0.000 | 0.000 | 0.000 |
| macro | strict | timex | 0.000 | 0.000 | 0.000 |
| macro | strict | relation | 0.073 | 0.333 | 0.120 |
| macro | relaxed | entity | 0.064 | 0.176 | 0.094 |
| macro | relaxed | event | 0.169 | 0.824 | 0.280 |
| macro | relaxed | timex | 0.000 | 0.000 | 0.000 |
| macro | relaxed | relation | 0.073 | 0.333 | 0.120 |

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.000
- Strict TIMEX F1: 0.000
- Strict Relation F1: 0.120
- Composite: 0.036

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.280
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.084

## Projection Determinism

- Deterministic: False
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.000 below threshold 0.50 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: micro F1=0.000 below threshold 0.50 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- relation: micro F1=0.120 below threshold 0.50 - mark as priority optimization track.
- timex: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- timex: micro F1=0.000 below threshold 0.50 - mark as priority optimization track.

## Hotspot Documents

| Doc ID | Avg F1 | Weak Layers |
|---|---:|---|
| 76437 | 0.030 | entity, event, timex, relation |

## Per-Document Diagnostics

### Doc 76437

- Avg F1: 0.030
- Weak layers: entity, event, timex, relation

| Layer | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| entity | 0 | 47 | 17 | 0.000 | 0.000 | 0.000 |
| event | 0 | 83 | 17 | 0.000 | 0.000 | 0.000 |
| timex | 0 | 0 | 4 | 0.000 | 0.000 | 0.000 |
| relation | 7 | 89 | 14 | 0.073 | 0.333 | 0.120 |

Suggested actions:
- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.000) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- entity: type mismatches detected - tune label/attribute mapping in mapping-config.
- event: low F1 (0.000) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.120) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.000) - inspect extraction and matching rules for this layer.
- timex: recall is weaker than precision - investigate under-generation and missing extractions.

Top failure examples:
- entity:
- boundary_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [57, 58, 59, 60, 61], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [58], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [69, 70, 71, 72], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [72], 'attrs': {'ent_class': 'GEN', 'syntactic_type': 'PTV'}}
- type_mismatch (2 shown):
  - gold={'kind': 'entity', 'span': [28, 29, 30], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [28, 29, 30], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'NAM'}}
  - gold={'kind': 'entity', 'span': [69], 'attrs': {'syntactic_type': 'NAM'}} | predicted={'kind': 'entity', 'span': [69], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'NAM'}}
- missing (5 shown):
  - gold={'kind': 'entity', 'span': [1], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [11, 12, 13], 'attrs': {'syntactic_type': 'NOM'}}
  - gold={'kind': 'entity', 'span': [23, 24, 25], 'attrs': {}}
- spurious (5 shown):
  - predicted={'kind': 'entity', 'span': [7, 8, 9, 10], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'NAM'}}
  - predicted={'kind': 'entity', 'span': [44, 45, 46], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'PTV'}}
  - predicted={'kind': 'entity', 'span': [53, 54], 'attrs': {'ent_class': 'SPC', 'syntactic_type': 'PTV'}}
- event:
- boundary_mismatch (5 shown):
  - gold={'kind': 'event', 'span': [43], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [43], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e7', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [49], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'end', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [49], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e8', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'end', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [62], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [62], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e9', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
- type_mismatch (5 shown):
  - gold={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [2, 3], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e1', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'drag down', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [14], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e2', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'fall', 'tense': 'PAST', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [21], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'stem', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}} | predicted={'kind': 'event', 'span': [21], 'attrs': {'aspect': 'NONE', 'certainty': 'CERTAIN', 'external_ref': 'e4', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'stem', 'tense': 'PRESPART', 'time': 'NON_FUTURE'}}
- missing (5 shown):
  - gold={'kind': 'event', 'span': [6], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'crisis', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [20], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'sell-off', 'time': 'NON_FUTURE'}}
  - gold={'kind': 'event', 'span': [92], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'add', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
- spurious (5 shown):
  - predicted={'kind': 'event', 'span': [84], 'attrs': {'certainty': 'CERTAIN', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'are', 'time': 'NON_FUTURE'}}
  - predicted={'kind': 'event', 'span': [92], 'attrs': {'aspect': 'NONE', 'certainty': 'POSSIBLE', 'external_ref': 'e12', 'polarity': 'POS', 'pos': 'VERB', 'pred': 'add', 'tense': 'INFINITIVE', 'time': 'FUTURE'}}
  - predicted={'kind': 'event', 'span': [93], 'attrs': {'certainty': 'CERTAIN', 'external_ref': 'e13', 'polarity': 'POS', 'pos': 'NOUN', 'pred': 'liquidity', 'time': 'NON_FUTURE'}}
- timex:
- missing (4 shown):
  - gold={'kind': 'timex', 'span': [7, 8, 9, 10], 'attrs': {'functionInDocument': 'CREATION_TIME', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [15], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
  - gold={'kind': 'timex', 'span': [38, 39, 40, 41], 'attrs': {'functionInDocument': 'NONE', 'type': 'DATE', 'value': '2007-08-10'}}
- relation:
- endpoint_mismatch (1 shown):
  - gold=('has_participant', 'event', (73,), 'entity', (69, 70, 71, 72), ()) | predicted=('has_participant', 'event', (73,), 'entity', (69, 70, 71), ())
- missing (5 shown):
  - gold=('has_participant', 'event', (26,), 'entity', (28, 29, 30), ())
  - gold=('has_participant', 'event', (62,), 'entity', (57, 58, 59, 60, 61), ())
  - gold=('tlink', 'event', (14,), 'event', (37,), (('reltype', 'BEFORE'),))
- spurious (5 shown):
  - predicted=('clink', 'event', (230,), 'event', (233,), ())
  - predicted=('clink', 'event', (230,), 'event', (237,), ())
  - predicted=('clink', 'event', (233,), 'event', (237,), ())
