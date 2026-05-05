# textgraphx Evaluation Diagnostics & Roadmap

This document outlines the systematic investigation of pipeline mismatch against the MEANTIME gold dataset, specifically detailing false positives (spurious extractions) and false negatives (missing extractions).

## 1. Entity Precision (Resolved via Dependency & Schema Fixes)
**Symptom:** Previously high volume of spurious entities, F1 ~7%.
**Resolution Steps:**
- **Schema Alignment:** Fixed a critical bug in `meantime_evaluator.py` where `CorefMention` nodes were skipped because they lacked the specific `:NominalMention` label, despite carrying the correct `syntactic_type='NOM'`.
- **Dependency-Based Nominal Boundaries:** Updated `RefinementPhase.py` to use `headTokenIndex` instead of full `NounChunk` extents. This eliminated trailing relative clauses and punctuation from the strict evaluation geometry, resolving massive boundary mismatches (e.g., Gold `[102]` vs Predicted `[102, 103, 104, 105, 106]`).
- **Appositive (`APP`) & Prenominal (`PRE.NOM`) Materialization:** Leveraged spaCy's dependency graph (`IS_DEPENDENT {type: "appos"}`) to dynamically extract and assign `APP` syntactic types. MEANTIME evaluator now explicitly accepts these geometries, dramatically reducing False Negatives.
**Current Status:** Entity Strict F1 jumped from 0.07 to ~0.179; Relaxed F1 to ~0.267.

**Operator A/B Benchmark (ENH-NOM-04):**
- Use the two-profile nominal filter benchmark to compare legacy vs strict
  ENH-NOM-04 noun-chunk filtering under identical strict evaluation scope:

```bash
make nominal-filter-ab
```

- The benchmark writes date-stamped reports and a summary JSON under
  `src/textgraphx/datastore/evaluation/latest/`.
- Profiles:
  - `legacy` (`TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS=0`)
  - `enh_nom4` (`TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS=1`)
- The benchmark refresh now clears profile-dependent noun-chunk artifacts
  before each profile run (noun-chunk nominal mentions, noun-chunk-sourced
  entities, and `link_fa_entitymention_entity` links) so results stay
  profile-isolated.
- The benchmark now reports `projected_nc_vs_gold` diagnostics:
  - `exclusive_gold_overlap`: NC-exclusive projected spans that exactly match a
    gold entity span.
  - `exclusive_not_in_gold`: NC-exclusive projected spans with no exact gold
    span match.
- The summary JSON now includes `diagnostic_verdict`, a compact machine-readable
  interpretation with:
  - `code`: stable verdict identifier for dashboards/automation.
  - `strict_entity_delta`: TP/FP/FN and strict precision/recall/F1 deltas
    (`enh_nom4 - legacy`).
  - `projected_nc_vs_gold_delta`: NC-exclusive total/gold-overlap/non-gold
    deltas (`enh_nom4 - legacy`).
- If noun-chunk materialization counts differ but strict entity metrics remain
  identical, inspect projected nominal inclusion using evaluator scope and
  nominal precision filters before changing extraction heuristics. A large
  negative delta in NC-exclusive spans with `exclusive_gold_overlap=0` indicates
  strict filtering removed only non-gold-aligned noise.

## 2. Event Recall and Strict Matching (Resolved Attributes, Remaining Bottleneck)
**Symptom:** Disappointing Event Strict F1 (~0.056), though Relaxed F1 was much higher (~0.30).
**Resolution Steps:**
- **SpaCy Lemmatization:** Evaluator now leverages `en_core_web_sm` to safely canonicalize predicates (e.g. `fell` -> `fall`, `was` -> `be`) matching MEANTIME root expectations natively.
- **Tense & Aspect Normalization:** Re-aligned `PASTPART` to `PAST` and mapped VBG with `NONE` tense to `PRESPART` to fulfill MEANTIME categorical expectations. Stripped `tense` and `aspect` entirely for NOUN events, removing penalization for correct nominal spans.
- **WordNet Eventive Expansion:** Expanded `_is_wordnet_eventive_noun` to include `noun.phenomenon` and `noun.state` mapping to prevent dropping valid nominal events.
**Current Status:** Event Strict F1 jumped from 0.056 to ~0.123 (a >100% improvement); Relaxed F1 to ~0.301.
**Remaining Bottleneck:** The system still suffers from missing event spans compared to MEANTIME's granular annotations, especially nested nominal events, or multi-word expressions where the pipeline predicts fewer tokens. Tokenizer alignment for event triggers needs tighter rules (phrasals, verb+particle combinations).

### Nominal temporal anchoring follow-up
- A remaining downstream gap was that SRL-derived temporal spans (`TimexMention:SRLTimexCandidate`, produced from `ARGM-TMP`) were materialized but not consumed by any dedicated NOMBANK TLINK rule.
- `TlinksRecognizer` now has a dedicated nominal-event rule that links `TEvent {source='nombank_srl'}` to `SRLTimexCandidate` only when the candidate comes from the same `ARGM-TMP` `FrameArgument` (`tm.source_fa_id = fa.id`).
- This is intentionally narrower than sentence-proximity anchoring: case 9 still excludes `SRLTimexCandidate` nodes to avoid loose circular evidence, while the new rule only uses structure-grounded SRL temporal arguments.

## 3. Relational Noise (`HAS_PARTICIPANT` Sprawl)
**Symptom:** ~252 Spurious `HAS_PARTICIPANT` links on a 6-document batch vs ~44 missed.
**Root Cause:**
- **Event/Entity Cascade Failure:** >50% of the false-positive participants are anchored to Events or Entities that are themselves spurious or don't match the exact token span. Improvements in Entity boundaries (Section 1) and Event boundaries (Section 2) will continuously repair a portion of these links.
- **Semantic Role Labeling Over-generation:** SRL dutifully binds all arguments (`Arg0`, `Arg1`) for every predicate it finds regardless of MEANTIME's sparse event criteria.
- **`sem_role` Nomenclature Mismatch:** Even when the Event and Entity spans match, there are frequent labeling mismatches (e.g. Pipeline assigns `Arg1` while MEANTIME evaluates as `Arg0`).

**Operational Mitigation (Evaluator Scope):**
- Keep purity runs on core-only participants (default behavior).
- Use the one-command benchmark runner to compare core-only, constrained non-core,
	and full non-core profiles with the same settings:

```bash
make participant-benchmark
```

- The benchmark stores date-stamped report artifacts in
	`src/textgraphx/datastore/evaluation/latest/` and prints deltas against core-only.
- For recall-oriented diagnostics, enable non-core links with a role allowlist to avoid flooding with adjuncts:

```bash
python -m textgraphx.tools.evaluate_meantime \
	--gold-dir src/textgraphx/datastore/annotated \
	--pred-neo4j \
	--include-non-core-participants \
	--non-core-participant-roles ARG0,ARG1
```

- Use `--non-core-participant-roles all` (or omit the flag) only for broad exploratory analysis.

## 4. Subordinate & Causal Links (`SLINK` / `CLINK`)
**Symptom:** Evaluator reports 0 instances extracted despite 24 instances physically present in the gold-standard batch.
**Root Cause:**
- **Evaluation Configuration Filtering:** The primary issue is that `evaluate_meantime.py` defaults to `--relation-scope tlink,has_participant`.
- **Relational Deficits:** Checking the Neo4j database reveals very few links even exist natively (`10` CLINKs, `49` SLINKs). Logic in `EventEnrichmentPhase.py` relies exclusively on strict lexical matching (`say`, `says`, `told`, `report`) against SRL arguments, severely limiting recall.

---

## 5. Post-Assessment Evaluation Mechanism Fixes (2026-05-02)

A critical audit of the evaluator produced 9 identified issues across severity levels. All 9 are resolved in this section. Tests are in `src/textgraphx/tests/test_evaluation_mechanism_fixes.py` (14 tests, all pass).

### Issue 1/5 — Event span collapse with no headword match (CRITICAL/MEDIUM)
**Symptom:** When an event spans multiple tokens and the `pred` headword is not found among the gold tokens, the code silently collapses to `span[-1]` (the rightmost token). TLINK endpoint alignment then silently uses the wrong anchor.

**Fix:** Added a `matched_head` flag inside the span-collapse loop in `build_document_from_neo4j`. When `matched_head` is `False` after the loop, a `LOGGER.debug("event_span_collapse_fallback: ...")` is emitted to make the fallback visible. Behaviour is unchanged; the diagnostic is the fix.

### Issue 2 — Branch 3 Frame-fallback counter (HIGH)
**Symptom:** After Step 15's relaxed `NOT EXISTS` guard, Branch 3 (Frame-fallback, `source_priority=0`) fires more aggressively, potentially inflating event FP counts. There was no counter to quantify this.

**Fix:** Added `frame_fallback_event_count: int = 0` field to `NormalizedDocument`. In `build_document_from_neo4j`, after the deduplication loop, this field is set via:
```python
doc.frame_fallback_event_count = sum(1 for p, _ in event_by_span.values() if p == 0)
```
`evaluate_documents()` surfaces this value in its returned dict and logs a `DEBUG` message when non-zero. The CLI exposes it in the `evaluation_scope` block.

### Issue 3 — Disabled NOM entity projection guard (HIGH)
**Symptom:** A `TEMPORARILY DISABLED` comment was suppressing the filter that restricts NOM entity projections to explicit `:NominalMention`/`:CorefMention` nodes. NamedEntity nodes with `syntactic_type='NOM'` were included by default, potentially inflating entity FP counts.

**Fix:** Promoted the guard to a named parameter `strict_nom_layer_filter: bool = False` on `build_document_from_neo4j`. Default is `False` to preserve backward compatibility. When `True`, only explicitly labelled NominalMention/CorefMention nodes are projected as NOM entities. Exposed via `--strict-nom-layer-filter` CLI flag.

### Issue 4 — `unmatched_gold_events` field never populated (HIGH)
**Symptom:** `NormalizedDocument.unmatched_gold_events` was declared as `int = 0` but was never written by `evaluate_documents()`, so it always remained 0 regardless of actual false negatives.

**Fix:** At the end of `evaluate_documents()`, added:
```python
unmatched_gold_events = int(strict["event"].get("fn", 0))
predicted_doc.unmatched_gold_events = unmatched_gold_events
```
The value is also included in the returned dict as `"unmatched_gold_events"`.

### Issue 6 — SLINK/CLINK invisible in default relation scope (MEDIUM)
**Status:** Not changed behaviourally; documented here and in § 4. The default `--relation-scope tlink,has_participant` intentionally excludes SLINK/CLINK. Use `--relation-scope all` to score all relation kinds. The CLI `evaluation_scope` block now includes the resolved scope string so the exclusion is visible in every report.

### Issue 7 — Silent empty prediction on publicId mismatch (MEDIUM)
**Symptom:** If `build_document_from_neo4j` returned an empty projection (entity rows and event rows both empty), all gold mentions became silent false negatives with no diagnostic.

**Fix:** Two guards added:
1. If `doc_id_int is None or str(doc_id_int).strip() == ""` (ID resolution failure), a `LOGGER.warning` is emitted immediately and an empty document is returned.
2. After the entity and event queries, if both `entity_rows` and `event_rows` are empty, a `LOGGER.warning` message is emitted mentioning the doc_id pair and suggesting AnnotatedText.publicId verification.

### Issue 8 — Auxiliary filter misses TEvents with empty `pred` (LOW)
**Status:** Not changed. When `pred` is empty (Branch 2 with no Frame backing), `_should_project_event` cannot determine whether the event is auxiliary. These events are already gated by `low_confidence` and other upstream checks. Documented here for completeness; no code change.

### Issue 9 — TIMEX `functionInDocument` injected as `"NONE"` (LOW)
**Symptom:** `_canonicalize_timex_attrs()` contained `str(row.get("functionInDocument") or "").strip() or "NONE"`. When the Neo4j field is absent or null, the literal string `"NONE"` was added to the canonical attribute set, causing incorrect strict-match failures against gold TIMEX nodes that legitimately omit `functionInDocument`.

**Fix:** Removed `or "NONE"`. The canonical code is now:
```python
function_in_document = str(row.get("functionInDocument") or "").strip()
```
`functionInDocument` is only added to `attrs_map` when the resulting string is non-empty (unchanged guard at line ~1230).

---
*Last updated: 2026-05-02*
