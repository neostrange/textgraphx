# Evaluation Report

- Mode: single
- Document id: 76437

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.297
- Strict TIMEX F1: 0.235
- Strict Relation F1: 0.102
- Composite: 0.220

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.027
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.008

## Projection Determinism

- Deterministic: True
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.137) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.297) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: type mismatches detected - tune label/attribute mapping in mapping-config.
- relation: low F1 (0.102) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
