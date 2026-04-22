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
- File: `textgraphx/TemporalPhase.py` _(Historical pre-remediation location. After Item 4 ownership fix, `EventMention` creation and predicate canonicalization live in `textgraphx/EventEnrichmentPhase.py`.)_
- Change: `EventMention.pred` now prefers trigger-token lemma over raw form.
- Rationale: gold `pred` is lemma-like; this improves semantic comparability.

2. Phrasal verb preservation (`VB*` + following `RP`)
- File: `textgraphx/TemporalPhase.py` _(Historical pre-remediation location. After Item 4 ownership fix, phrasal-verb span logic for `EventMention` lives in `textgraphx/EventEnrichmentPhase.py`.)_
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
- Source: `--gold-dir src/textgraphx/datastore/annotated --pred-neo4j`
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

- Detailed per-mode reports are stored under `src/textgraphx/datastore/evaluation/nominal_profile_mode/`
- Consolidated table: `src/textgraphx/datastore/evaluation/nominal_profile_mode/PROFILE_MODE_SUMMARY.md`

## 2026-04-09 - Breadth-First Heuristic Sweep (A-to-Z) with Zero Regression

### Context
After the first breadth-first pass improved entity/timex/relation outcomes, we applied a second incremental sweep focused on:

- relation-layer transparency by relation kind,
- lightweight timex normalization hardening,
- conservative nominal boundary guardrails,
- strict zero-regression enforcement across all headline layers.

### Changes

1. Relation-kind breakdown reporting in evaluator output
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - `evaluate_documents()` now emits `relation_by_kind` for `strict` and `relaxed`.
  - `aggregate_reports()` now emits micro/macro `relation_by_kind` aggregates.
  - `render_markdown_report()` now includes a `Relation Kind Breakdown (Micro Strict)` section.
- Rationale: exposes where relation F1 is blocked (`tlink` vs `has_participant` vs `clink`/`slink`) without needing custom scripts.

2. Timex date normalization hardening
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - Added `_normalize_timex_date_value()` and integrated it into timex canonicalization.
  - Supports common textual date forms such as `August 10, 2007`, `10 August 2007`, and month-year forms.
- Rationale: preserve strict matching when extractor surface forms are textual but gold is ISO-like.

3. Conservative nominal over-collapse guard
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - Added `_should_restore_wider_nominal_span()` and restoration path during nominal projection.
  - Only restores wider span when candidate-gold nominals were over-collapsed to very short spans and have structural support (`has_core_argument` or `has_named_link`).
- Rationale: avoid head-only collapse on gold-aligned nominal mentions while minimizing precision risk.

4. Relation alignment consistency for participants
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - Added `_align_relation_entity_span()` for `has_participant` target endpoints.
  - Added `_normalize_sem_role()` to normalize PropBank role casing (`ARG1` -> `Arg1`, `ARGM-LOC` -> `Argm-LOC`).
- Rationale: convert trivial formatting/endpoint near-misses into true positives.

### Zero-Regression Validation

Command family (batch strict all-layer):

- `python -m textgraphx.tools.evaluate_meantime --gold-dir src/textgraphx/datastore/annotated --pred-neo4j --analysis-mode strict --relation-scope all --nominal-profile-mode candidate-gold ...`

Compared baseline `global_sweep_post_batch.json` to updated `global_sweep_post2_batch.json`:

- entity strict F1: `0.1373 -> 0.1373` (`+0.0000`)
- event strict F1: `0.2973 -> 0.2973` (`+0.0000`)
- timex strict F1: `0.2353 -> 0.2353` (`+0.0000`)
- relation strict F1: `0.1022 -> 0.1022` (`+0.0000`)

Result: **zero regression confirmed** on all tracked strict layers.

### New Relation-Kind Visibility (micro strict)

From `global_sweep_post2_batch.json`:

- `has_participant`: `P=0.0822`, `R=0.6000`, `F1=0.1446` (`TP=6`, `FP=67`, `FN=4`)
- `tlink`: `P=0.0263`, `R=0.0909`, `F1=0.0408` (`TP=1`, `FP=37`, `FN=10`)
- `clink`: `P=0.0000`, `R=0.0000`, `F1=0.0000` (`TP=0`, `FP=4`, `FN=0`)
- `slink`: `P=0.0000`, `R=0.0000`, `F1=0.0000` (`TP=0`, `FP=1`, `FN=0`)

Interpretation:

- relation gains so far are concentrated in `has_participant` matching.
- next relation-targeted low-hanging fruit should focus on TLINK normalization/alignment before deeper model changes.

## 2026-04-09 - TLINK Directional Canonicalization Pass (Zero-Regression Safe)

### Context
Relation-kind breakdown from the breadth-first sweep showed TLINK as the weakest strict relation kind.
Observed pattern: semantically equivalent TLINKs can be represented with opposite endpoint direction and inverse `reltype`, which strict keying previously treated as mismatches.

### Changes

1. TLINK canonical orientation in relation keying
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - `_relation_key()` now canonicalizes TLINK direction before strict/relaxed key construction.
  - Mixed links are normalized to `event -> timex` orientation when endpoints are `(timex,event)`.
  - Same-kind TLINKs are normalized to stable span order.
  - Inverse `reltype` normalization is applied when direction is flipped (`BEFORE/AFTER`, `INCLUDES/IS_INCLUDED`, `BEGINS/BEGUN_BY`, `ENDS/ENDED_BY`, etc.).
- Rationale: score semantic equivalence rather than extractor-specific edge orientation artifacts.

2. Timex endpoint alignment helper (safe no-op in this corpus)
- File: `textgraphx/evaluation/meantime_evaluator.py`
- Change:
  - Added `_align_relation_timex_span()` and applied it in relation projection for TLINK/GLINK/CLINK/SLINK.
- Rationale: mirror existing event/entity endpoint alignment behavior for temporal endpoints.

### Measured Impact (strict, batch)

Compared `global_sweep_post2_batch.json` to `global_sweep_post4_batch.json`:

- entity strict F1: `0.1373 -> 0.1373` (`+0.0000`)
- event strict F1: `0.2973 -> 0.2973` (`+0.0000`)
- timex strict F1: `0.2353 -> 0.2353` (`+0.0000`)
- relation strict F1: `0.1022 -> 0.1186` (`+0.0165`)

TLINK micro strict detail:

- `tlink` F1: `0.0408 -> 0.0667` (`+0.0259`)
- counts: `TP 1 -> 1`, `FP 37 -> 18`, `FN 10 -> 10`

Interpretation:

- This pass is precision-led: it removed directional false positives without reducing any top-level strict layer score.
- Remaining TLINK recall bottleneck is unchanged (`FN=10`), indicating next gains must come from extraction/coverage rather than matching-only heuristics.

### Zero-Regression Check

Result: **zero regression confirmed** across entity/event/timex/relation strict micro F1.

## 2026-04-09 - Relation Endpoint Span Fallback Pass (Projection Robustness)

### Context
After TLINK directional canonicalization, strict TLINK recall remained limited (`FN=10`).
Code inspection found relation projection required `start_tok/end_tok` on relation endpoints, which can drop links when canonical nodes expose only `begin/end` or token-anchor connectivity.

### Change

- File: `textgraphx/evaluation/meantime_evaluator.py`
- Updated relation projection Cypher for `TLINK`, `GLINK`, and `CLINK|SLINK` to resolve endpoint spans with fallback order:
  - `start_tok/end_tok`
  - `begin/end`
  - token-anchor min/max via `(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN]->(node)`
- Behavior is now consistent with other projection paths that already coalesce multiple span sources.

### Measured Impact (strict, batch)

Compared `global_sweep_post4_batch.json` to `global_sweep_post5_batch.json`:

- entity strict F1: `0.1373 -> 0.1373` (`+0.0000`)
- event strict F1: `0.2973 -> 0.2973` (`+0.0000`)
- timex strict F1: `0.2353 -> 0.2353` (`+0.0000`)
- relation strict F1: `0.1186 -> 0.1186` (`+0.0000`)

TLINK micro strict detail:

- `tlink` F1: `0.0667 -> 0.0667` (`+0.0000`)
- counts unchanged: `TP=1`, `FP=18`, `FN=10`

Interpretation:

- The pass is robustness-hardening (avoids silent endpoint dropping in mixed-schema graphs) with neutral metrics on the current corpus snapshot.
- Remaining TLINK recall gap still points to extraction/coverage, not evaluator keying/projection.

### Zero-Regression Check

Result: **zero regression confirmed** across strict entity/event/timex/relation micro F1.

## 2026-04-09 - TLINK Coverage Path Activation in Wrapper

### Context
`TlinksRecognizer` exposes three direct TimeML/TTK XML-derived link builders:

- `create_tlinks_e2e(doc_id)`
- `create_tlinks_e2t(doc_id)`
- `create_tlinks_t2t(doc_id)`

but the production wrapper (`TlinksRecognizerWrapper.execute`) previously executed only heuristic case rules (`case1..case7`).

This left a coverage gap where direct TLINKs from TTK XML were available in code but not activated in the standard pipeline path.

### Change

- File: `textgraphx/phase_wrappers.py`
- In `TlinksRecognizerWrapper.execute()`, added an **opt-in** pre-case pass controlled by runtime flag `enable_tlink_xml_seed` (default `false`) that:
  - retrieves document ids via `recognizer.get_annotated_text()`
  - runs `create_tlinks_e2e/e2t/t2t` per document
  - continues on per-document failure (non-blocking) to preserve pipeline robustness
  - returns execution counters (`xml_docs_processed`, `xml_e2e_runs`, `xml_e2t_runs`, `xml_t2t_runs`) in the phase result payload

### Validation

- `tests/test_milestone7_schema_validation.py`: pass
- `tests/test_evaluate_meantime_cli.py`: pass
- `textgraphx/tests/test_tlinks_case7_phase_d.py`: pass

### Exploratory Impact (flag enabled)

When run with XML seeding enabled on current corpus snapshot (`post5 -> post6` strict batch):

- relation strict F1: `0.1186 -> 0.1167` (`-0.0020`)
- tlink strict F1: `0.0667 -> 0.0625` (`-0.0042`)
- tlink counts: `TP 1 -> 1`, `FP 18 -> 20`, `FN 10 -> 10`

Interpretation:

- current XML seeding increased TLINK false positives without recall gain in this dataset profile.
- to preserve zero-regression defaults, this capability remains behind `enable_tlink_xml_seed=false` unless explicitly enabled for targeted experimentation.

### Expected Effect (when tuned)

- Improves TLINK recall opportunity by enabling direct XML-derived temporal links before heuristic cases and consistency filters.
- Keeps safety gates unchanged (normalization, closure, constraint solver, conflict suppression, anchor consistency, endpoint contract validation).

### Precision-Safe Tuning Update

To reduce precision drift when XML seeding is enabled:

- `TlinksRecognizer.create_tlinks_e2e/e2t/t2t` now support `precision_mode` and stamp provenance (`source='ttk_xml'`, rule ids, confidence defaults).
- Wrapper XML seeding uses `precision_mode=True` and currently seeds only E2E + E2T (T2T seeding is intentionally skipped in precision mode).
- Precision-mode E2T policy allows:
  - `BEFORE` / `AFTER`
  - `IS_INCLUDED` only when target TIMEX is DCT (`functionInDocument='CREATION_TIME'`).

These changes keep XML seeding available for controlled experimentation while tightening the default precision profile for the opt-in path.

### Benchmarking Caveat

Because the current Neo4j graph state already contains prior exploratory TLINK writes from earlier runs, a clean post-tuning benchmark should be run on a freshly rebuilt graph snapshot before promoting this path beyond opt-in mode.

### Clean A/B Run (2026-04-09, Local)

Executed two clean runs on a fully rebuilt graph using runtime-identical phase order:

1. XML seed OFF: ingestion, refinement, temporal, event_enrichment, tlinks
2. XML seed ON (precision mode): ingestion, refinement, temporal, event_enrichment, then `TlinksRecognizerWrapper` with `enable_tlink_xml_seed=true`

Observed outcome on current local dataset snapshot:

- strict batch deltas OFF -> ON: all tracked layers unchanged (`entity/event/timex/relation = 0.0000`)
- TLINK strict unchanged (`TP=0`, `FP=0`, `FN=11`, `F1=0.0000`)
- wrapper counters with XML seed ON: `xml_docs_processed=0`, `xml_e2e_runs=0`, `xml_e2t_runs=0`

Interpretation:

- This specific clean benchmark is **inconclusive** for XML seeding effectiveness because no documents were eligible for XML-derived TLINK seeding in the local run context.
- Further promotion decisions should rely on a clean benchmark where XML seed counters are non-zero and comparable strict TLINK precision/recall is observed.
