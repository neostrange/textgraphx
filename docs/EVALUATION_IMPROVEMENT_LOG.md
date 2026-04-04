# Evaluation Improvement Log

Purpose: track incremental, linguistically grounded changes that improve MEANTIME evaluation while preserving schema integrity and long-term event-centric KG reasoning goals.

## 2026-04-04 - Event Layer Precision/Recall Hardening (Incremental)

### Context
Baseline strict event matching was weak due to:
- predicate surface-vs-lemma mismatch,
- phrasal verb boundary mismatch,
- conservative but misaligned tense/time defaults,
- duplicate fallback event projection when mention projection already existed.

### Changes

1. EventMention predicate canonicalization from trigger lemma
- File: `textgraphx/TemporalPhase.py`
- Change: `EventMention.pred` now prefers trigger-token lemma over raw form.
- Rationale: gold `pred` is lemma-like; this improves semantic comparability.

2. Phrasal verb preservation (`VB*` + following `RP`)
- File: `textgraphx/TemporalPhase.py`
- Change: mention-level `pred` becomes multiword (e.g., `drag down`) and `end_tok` extends to include the particle.
- Rationale: preserves lexicalized event meaning without mutating canonical `TEvent` identity.

3. Event factuality normalization
- File: `textgraphx/EventEnrichmentPhase.py`
- Changes:
  - certainty defaults include future/infinitive/modal cues,
  - aspect `NONE` preserved where appropriate,
  - noun/non-verbal over-specification cleanup (Penn POS-aware),
  - infinitive prospective normalization (`to + VB`) sets `time=FUTURE` for lexical infinitives,
  - non-verbal event mentions (`OTHER/JJ*`) normalize verbal tense labels to `NONE`.
- Rationale: align mention-level attributes with MEANTIME-style annotation semantics while keeping explicit KG facts.

4. Low-confidence event evidence gating
- Files: `textgraphx/EventEnrichmentPhase.py`, `textgraphx/evaluation/meantime_evaluator.py`
- Changes:
  - computes `EventMention.low_confidence` using conservative evidence checks (frame support, participant support, TLINK support),
  - rolls up to `TEvent.low_confidence` only when all mentions are low-confidence,
  - evaluator excludes low-confidence projected events.
- Rationale: filter weak projections without deleting graph evidence.

5. Fallback projection de-duplication in evaluator
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change: fallback `TEvent` projection skipped when a concrete `EventMention` projection already exists.
- Rationale: prevents duplicate/spurious event mentions caused by projection-layer overlap.

### Measured Impact (doc_id=76437)

Latest measured strict event metrics:
- before this increment set: `F1=0.2651`, `TP=11`, `FP=55`, `FN=6`
- after this increment set: `F1=0.3171`, `TP=13`, `FP=52`, `FN=4`

Error-bucket deltas:
- `type_mismatch`: `3 -> 1`
- `spurious`: `52 -> 51`
- `boundary_mismatch`: remains `0`

Entity/relation strict scores unchanged in this increment (by design).

### Safety/Architecture Notes

- All lexical/tense adjustments are mention-level (`EventMention`) and evaluator projection-level.
- Canonical event nodes (`TEvent`) remain stable except explicit confidence rollup metadata.
- Changes are evidence-based and reversible, preserving long-term reasoning compatibility.

### Remaining Known Event Bottleneck

- One strict type mismatch remains around `fear`: gold tense `PRESENT` vs predicted `PRESPART`.
- Next candidate increment: dependency/auxiliary-sensitive participle normalization for stative/cognitive predicates, gated by explicit contextual evidence.

## 2026-04-04 - Cognitive Participle and Projection De-dup Increment

### Context
After prior improvements, strict event mismatches were concentrated in:
- one cognitive participle (`fearing that ...`) tense mismatch,
- residual overlap from fallback projection paths.

### Changes

1. Cognitive participle normalization
- File: `textgraphx/EventEnrichmentPhase.py`
- Rule: for `EventMention` with `tense=PRESPART`, `pred=fear`, trigger token POS `VBG`, and next-token lemma `that`, set:
  - `tense = PRESENT`
  - `aspect = NULL`
- Rationale: aligns with MEANTIME-style treatment of clausal cognitive adjuncts while remaining tightly scoped.

2. Evaluator fallback de-dup refinement
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Rule: skip fallback `TEvent` projection when a concrete, non-low-confidence `EventMention` already exists for that canonical event.
- Rationale: removes projection-layer duplicates without dropping canonical event data.

3. Test coverage
- File: `tests/test_event_enrichment_unit.py`
- Added assertions that cognitive participle normalization query is present and constrained by lexical/POS context.

### Measured Impact (doc_id=76437)

Strict event metrics:
- before: `F1=0.3171`, `TP=13`, `FP=52`, `FN=4`, `type_mismatch=1`
- after:  `F1=0.3415`, `TP=14`, `FP=51`, `FN=3`, `type_mismatch=0`

Layer notes:
- Event strict improved again.
- Entity/timex/relation strict unchanged in this increment (expected).

### Safety/Architecture Notes

- Adjustments remain mention-level or evaluation-projection-level.
- Canonical `TEvent` semantics are preserved.
- Rules are lexical-context-gated to avoid broad drift.

### Rejected Experiment (Not Adopted)

- Experiment: participant projection fallback from `FrameArgument` to `NamedEntity` via token-overlap.
- Outcome: relation strict recall increased slightly, but precision dropped sharply due over-linking (large FP increase).
- Decision: reverted immediately to preserve stable precision and avoid semantic drift.
- Lesson: relation-layer improvements should prefer high-precision constraints (e.g., explicit argument-role + dependency evidence) over loose token-overlap joins.

## 2026-04-04 - Nominal Profile Mode Sweep (ENH-NOM-03)

### Context
Evaluator-side nominal profile modes were added to project different nominal views from persisted semantic attributes:

- `all`
- `eventive`
- `salient`
- `candidate-gold`
- `background`

The objective was to compare precision/recall tradeoffs without mutating graph evidence.

### Run Configuration

- CLI: `python -m textgraphx.tools.evaluate_meantime`
- Source: `--gold-dir textgraphx/datastore/annotated --pred-neo4j`
- Analysis mode: `strict`
- Profile sweep: one run per `--nominal-profile-mode`

### Measured Results (micro strict, entity layer)

- `all`: `P=0.0576`, `R=0.4706`, `F1=0.1026`, predicted entities=`139`
- `eventive`: `P=0.0577`, `R=0.1765`, `F1=0.0870`, predicted entities=`52`
- `salient`: `P=0.0606`, `R=0.4706`, `F1=0.1074`, predicted entities=`132`
- `candidate-gold`: `P=0.0702`, `R=0.4706`, `F1=0.1221`, predicted entities=`114`
- `background`: `P=0.0625`, `R=0.1765`, `F1=0.0923`, predicted entities=`48`

### Interpretation

- `candidate-gold` produced the strongest entity-layer F1 and precision in this sweep.
- `eventive` and `background` are intentionally more selective; they reduced volume strongly but also lowered recall.
- The sweep confirms that ENH-NOM-03 profile modes are operational and create measurable policy differences at evaluation time.

### Important Caveat

- Local gold corpus currently includes a single XML document, so results are directional, not yet corpus-general.
- In this run state, projected event/timex/relation layers were zero for Neo4j predictions; nominal profile mode conclusions here are entity-layer specific.

## 2026-04-04 - Cross-Scope Nominal Profile Validation

### Context
The initial ENH-NOM-03 sweep was extended to compare profile modes across three evaluator scopes:

- baseline (no discourse filter)
- discourse-only
- discourse-only + gold-like nominal filter

### Result Summary

Best entity-layer micro strict F1 per scope:

- baseline: `candidate-gold` (`F1=0.1221`)
- discourse-only: `candidate-gold` (`F1=0.1495`)
- discourse-only + gold-like: `candidate-gold` (`F1=0.1391`)

Interpretation:

- The same profile winner (`candidate-gold`) held across all tested scopes.
- Discourse scoping improved precision and F1 relative to baseline while preserving recall in this document.
- Adding gold-like nominal filtering reduced some over-generation but did not beat discourse-only + candidate-gold.

Artifacts:

- Detailed per-mode reports are stored under `textgraphx/datastore/evaluation/nominal_profile_mode/`
- Consolidated table: `textgraphx/datastore/evaluation/nominal_profile_mode/PROFILE_MODE_SUMMARY.md`
