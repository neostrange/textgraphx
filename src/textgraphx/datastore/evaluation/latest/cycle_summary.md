# Cycle Summary

- Documents evaluated: 6
- Script: scripts/run_meantime_eval_cycle.sh
- Legacy relation scope: tlink
- Full relation scope: tlink,has_participant
- Fallback run used: true

## Micro F1 (Legacy Scope)
- entity: strict=0.2963, relaxed=0.3333
- event: strict=0.2314, relaxed=0.3033
- timex: strict=0.3789, relaxed=0.5263
- relation: strict=0.4854, relaxed=0.4063

## Micro F1 (Full Relation Scope)
- entity: strict=0.3045, relaxed=0.3417
- event: strict=0.2314, relaxed=0.3033
- timex: strict=0.3789, relaxed=0.5263
- relation: strict=0.2373, relaxed=0.2375

## Scorecards (Legacy Scope)
- TimeML compliance composite: 0.3519
- Beyond-TimeML reasoning composite: 0.0216

## Top Suggestions
- entity: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- entity: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- entity: micro F1=0.296 below threshold 0.75 - mark as priority optimization track.
- entity: type mismatch volume present - refine schema mapping and attribute projection.
- event: dataset-level precision gap - tighten confidence filters and post-processing constraints.
- event: high boundary mismatch volume - calibrate span normalization and tokenizer alignment.
- event: micro F1=0.231 below threshold 0.75 - mark as priority optimization track.
- event: type mismatch volume present - refine schema mapping and attribute projection.
- relation: dataset-level recall gap - prioritize recall-oriented rules and candidate generation.
- relation: micro F1=0.485 below threshold 0.75 - mark as priority optimization track.
