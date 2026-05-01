# Cycle Summary

- Documents evaluated: 6
- Script: scripts/run_meantime_eval_cycle.sh
- Legacy relation scope: tlink
- Full relation scope: tlink,has_participant
- Fallback run used: false

## Micro F1 (Legacy Scope)
- entity: strict=0.3058, relaxed=0.3431
- event: strict=0.2371, relaxed=0.3093
- timex: strict=0.3789, relaxed=0.5263
- relation: strict=0.1014, relaxed=0.0615

## Micro F1 (Full Relation Scope)
- entity: strict=0.2975, relaxed=0.3347
- event: strict=0.2371, relaxed=0.3093
- timex: strict=0.3789, relaxed=0.5263
- relation: strict=0.0968, relaxed=0.0665

## Scorecards (Legacy Scope)
- TimeML compliance composite: 0.2389
- Beyond-TimeML reasoning composite: 0.0216

## Top Suggestions
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
