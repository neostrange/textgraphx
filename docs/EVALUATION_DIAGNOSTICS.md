# textgraphx Evaluation Diagnostics & Roadmap

This document outlines the systematic investigation of pipeline mismatch against the MEANTIME gold dataset, specifically detailing false positives (spurious extractions) and false negatives (missing extractions).

## 1. Entity Precision (Resolved via Dependency & Schema Fixes)
**Symptom:** Previously high volume of spurious entities, F1 ~7%.
**Resolution Steps:**
- **Schema Alignment:** Fixed a critical bug in `meantime_evaluator.py` where `CorefMention` nodes were skipped because they lacked the specific `:NominalMention` label, despite carrying the correct `syntactic_type='NOM'`.
- **Dependency-Based Nominal Boundaries:** Updated `RefinementPhase.py` to use `headTokenIndex` instead of full `NounChunk` extents. This eliminated trailing relative clauses and punctuation from the strict evaluation geometry, resolving massive boundary mismatches (e.g., Gold `[102]` vs Predicted `[102, 103, 104, 105, 106]`).
- **Appositive (`APP`) & Prenominal (`PRE.NOM`) Materialization:** Leveraged spaCy's dependency graph (`IS_DEPENDENT {type: "appos"}`) to dynamically extract and assign `APP` syntactic types. MEANTIME evaluator now explicitly accepts these geometries, dramatically reducing False Negatives.
**Current Status:** Entity Strict F1 jumped from 0.07 to ~0.179; Relaxed F1 to ~0.267.

## 2. Event Recall and Strict Matching (Resolved Attributes, Remaining Bottleneck)
**Symptom:** Disappointing Event Strict F1 (~0.056), though Relaxed F1 was much higher (~0.30).
**Resolution Steps:**
- **SpaCy Lemmatization:** Evaluator now leverages `en_core_web_sm` to safely canonicalize predicates (e.g. `fell` -> `fall`, `was` -> `be`) matching MEANTIME root expectations natively.
- **Tense & Aspect Normalization:** Re-aligned `PASTPART` to `PAST` and mapped VBG with `NONE` tense to `PRESPART` to fulfill MEANTIME categorical expectations. Stripped `tense` and `aspect` entirely for NOUN events, removing penalization for correct nominal spans.
- **WordNet Eventive Expansion:** Expanded `_is_wordnet_eventive_noun` to include `noun.phenomenon` and `noun.state` mapping to prevent dropping valid nominal events.
**Current Status:** Event Strict F1 jumped from 0.056 to ~0.123 (a >100% improvement); Relaxed F1 to ~0.301.
**Remaining Bottleneck:** The system still suffers from missing event spans compared to MEANTIME's granular annotations, especially nested nominal events, or multi-word expressions where the pipeline predicts fewer tokens. Tokenizer alignment for event triggers needs tighter rules (phrasals, verb+particle combinations).

## 3. Relational Noise (`HAS_PARTICIPANT` Sprawl)
**Symptom:** ~252 Spurious `HAS_PARTICIPANT` links on a 6-document batch vs ~44 missed.
**Root Cause:**
- **Event/Entity Cascade Failure:** >50% of the false-positive participants are anchored to Events or Entities that are themselves spurious or don't match the exact token span. Improvements in Entity boundaries (Section 1) and Event boundaries (Section 2) will continuously repair a portion of these links.
- **Semantic Role Labeling Over-generation:** SRL dutifully binds all arguments (`Arg0`, `Arg1`) for every predicate it finds regardless of MEANTIME's sparse event criteria.
- **`sem_role` Nomenclature Mismatch:** Even when the Event and Entity spans match, there are frequent labeling mismatches (e.g. Pipeline assigns `Arg1` while MEANTIME evaluates as `Arg0`).

## 4. Subordinate & Causal Links (`SLINK` / `CLINK`)
**Symptom:** Evaluator reports 0 instances extracted despite 24 instances physically present in the gold-standard batch.
**Root Cause:**
- **Evaluation Configuration Filtering:** The primary issue is that `evaluate_meantime.py` defaults to `--relation-scope tlink,has_participant`.
- **Relational Deficits:** Checking the Neo4j database reveals very few links even exist natively (`10` CLINKs, `49` SLINKs). Logic in `EventEnrichmentPhase.py` relies exclusively on strict lexical matching (`say`, `says`, `told`, `report`) against SRL arguments, severely limiting recall.

---
*Last updated: 2026-04-10*
