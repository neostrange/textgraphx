# Evaluation Report

- Mode: single
- Document id: 76437

## Scorecards

### TimeML Compliance

- Strict Event F1: 0.242
- Strict TIMEX F1: 0.118
- Strict Relation F1: 0.105
- Composite: 0.164

### Beyond-TimeML Reasoning

- Event Gain (relaxed - strict): 0.044
- Relation Gain (relaxed - strict): 0.000
- Composite: 0.013

## Projection Determinism

- Deterministic: True
- Runs: 2
- Mismatch runs: none

## Suggestions

- entity: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold.
- entity: low F1 (0.178) - inspect extraction and matching rules for this layer.
- entity: precision is weaker than recall - investigate over-generation and filtering criteria.
- event: low F1 (0.286) - inspect extraction and matching rules for this layer.
- event: precision is weaker than recall - investigate over-generation and filtering criteria.
- relation: low F1 (0.105) - inspect extraction and matching rules for this layer.
- relation: precision is weaker than recall - investigate over-generation and filtering criteria.
- timex: low F1 (0.235) - inspect extraction and matching rules for this layer.
- timex: precision is weaker than recall - investigate over-generation and filtering criteria.
