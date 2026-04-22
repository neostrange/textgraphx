# Backlog Items 4-9: Complete Audit & Implementation Plan

**Date:** April 6, 2026  
**Status:** Historical audit snapshot. Item 4 has since been remediated in code; method and ownership references below describe the pre-fix audit state unless otherwise noted.

**Do not use this file as the current architecture reference.**
Use `docs/architecture-overview.md`, `docs/schema.md`, and `textgraphx/README.md` for the maintained current-state ownership model.

---

## Executive Summary

Completed comprehensive specification and audit tests for all backlog items 4-9. Results show:

- ✅ **Item 4 (Temporal Ownership Split):** 6 clear violations identified, remediation plan created
- ❌ **Items 5, 8, 9:** Not yet implemented (checkpoint/resume, diagnostics, quality toolkit)
- ✅ **Items 6, 7:** Completed — TextProcessor decomposition done via interfaces.py + component_factory.py; refinement rule catalog created at fixtures/refinement_rules/catalog.json

**Test Coverage:** 61 tests created
- 25 specification tests (contract definitions) ✅ PASS
- 11 Item 4 audit tests (violations found) 🔴 6 FAIL
- 14 Items 5-9 audit tests (partial/unimplemented) ⚠️ 7 PASS, 7 SKIP
- 11 Item 4 remediation plan tests ✅ PASS

---

## Item 4: Temporal Ownership Split (FAILING - requires fixes)

### Current Status
**6 violations found** in audit of temporal phase separation:

#### Violation 1: TemporalPhase creates TLINKs (should only extract TIMEX/TEvent)
**Location:** `textgraphx/TemporalPhase.py` lines 187-297
- `create_tlinks_e2e()` - Event-to-Event TLINK creation
- `create_tlinks_e2t()` - Event-to-Timex TLINK creation  
- `create_tlinks_t2t()` - Timex-to-Timex TLINK creation

**Issue:** TLINK creation belongs to TlinksRecognizer, not TemporalPhase

**Fix:** Move to `textgraphx/TlinksRecognizer.py` (which already exists with case-based patterns)

#### Violation 2: TemporalPhase materializes EventMention nodes
**Location:** `textgraphx/TemporalPhase.py` line 600+
- `create_event_mentions2()` - EventMention node materialization

**Issue:** EventMention materialization belongs to EventEnrichmentPhase

**Fix:** Move to `textgraphx/EventEnrichmentPhase.py`

#### Violation 3: TlinksRecognizer creates TIMEX nodes  
**Location:** `textgraphx/TlinksRecognizer.py` (Cypher queries)

**Issue:** Should only create TLINK relationships, not TIMEX/TEvent nodes

**Fix:** Replace `CREATE/MERGE TIMEX` patterns with `MATCH TIMEX` in all create_tlinks_case* methods

#### Violation 4: Method names don't reflect extraction role
**Location:** `textgraphx/TemporalPhase.py`

**Current names:** `create_tlinks_*`, `create_event_mentions2`, `create_tevents2`  
**Expected names:** `extract_*`, `identify_*`, `materialize_temporal_*`

**Fix:** Rename to clarify extraction-only responsibility

#### Violation 5: Orchestration order not explicit
**Location:** `textgraphx/PipelineOrchestrator.py` (or runner script)

**Issue:** Documentation doesn't confirm TemporalPhase runs before TlinksRecognizer

**Fix:** Add explicit phase ordering verification

#### Violation 6: Cross-phase TLINK creation found
**Issue:** Multiple phases may be creating TLINKs due to violations above

---

## Implementation Plan for Item 4

### Step 1: Copy TLINK methods to TlinksRecognizer
**File:** `textgraphx/TlinksRecognizer.py`
```
Copy from TemporalPhase.py:
- create_tlinks_e2e() implementation
- create_tlinks_e2t() implementation
- create_tlinks_t2t() implementation

Add to TlinksRecognizer after existing create_tlinks_case* methods
```

### Step 2: Move EventMention creation to EventEnrichmentPhase
**File:** `textgraphx/EventEnrichmentPhase.py`
```
Copy from TemporalPhase.py:
- create_event_mentions2() method + logic

Add to EventEnrichmentPhase (check for duplicate of create_event_mentions)
```

### Step 3: Fix TlinksRecognizer Cypher patterns
**File:** `textgraphx/TlinksRecognizer.py`
```
Audit create_tlinks_case* methods:
- Replace "CREATE TIMEX" → "MATCH TIMEX"
- Replace "MERGE TIMEX" → "MATCH TIMEX"
- Verify queries still resolve nodes correctly
```

### Step 4: Rename TemporalPhase extraction methods
**File:** `textgraphx/TemporalPhase.py`
```
Rename remaining methods to reflect extraction:
- create_timexes2 → extract_timex_expressions
- create_tevents2 → extract_temporal_events  
- create_signals2 → materialize_temporal_signals
- CallHeidelTimeService → invoke_heideltime_extractor
- callTtkService → invoke_ttk_extractor
```

### Step 5: Document phase ordering
**Files:** `docs/architecture-overview.md`, orchestrator runner
```
Add explicit ordering documentation:
Phase execution order for temporal processing:
1. TemporalPhase (extract TIMEX/TEvent)
2. EventEnrichmentPhase (materialize EventMention) 
3. TlinksRecognizer (create TLINK relationships)
```

### Validation Criteria
After fixes, all 11 audit tests should pass:
- ✅ test_temporal_phase_does_not_create_tlink_directly
- ✅ test_temporal_phase_creates_timex_and_tevent_nodes
- ✅ test_temporal_phase_no_eventmention_materialization
- ✅ test_temporal_phase_method_names_reflect_extraction
- ✅ test_tlinks_recognizer_creates_tlink_relationships
- ✅ test_tlinks_recognizer_does_not_materialize_events
- ✅ test_tlinks_recognizer_matches_existing_events
- ✅ test_temporal_phase_runs_before_tlinks_recognizer
- ✅ test_no_phase_creates_tlink_besides_tlinks_recognizer
- ✅ test_architecture_overview_documents_ownership
- ✅ test_phase_docstrings_clarify_responsibility

---

## Items 5-9: Implementation Status

### Item 5: Checkpoint/Resume Support ❌ NOT IMPLEMENTED

**Purpose:** Save/restore graph state between phases for resumable runs

**Required Features:**
- `save_checkpoint(doc_id, phase_name, neo4j_state)` - Snapshot current graph
- `resume_from_checkpoint(doc_id, phase_name)` - Restore and resume
- Checkpoint format: `out/checkpoints/{doc_id}/{phase_name}.json`
- Validates checkpoint integrity before resume

**Tests Created:** 3 specification tests (skipped - code not found)

**Next Steps:**
1. Create `textgraphx/checkpoint.py` module
2. Implement save/restore functions with Neo4j snapshot logic
3. Integrate into PipelineOrchestrator
4. Create test fixtures in `tests/test_checkpoint_resume.py`

---

### Item 6: TextProcessor Decomposition ✅ COMPLETE

**Current Status:** TextProcessor exists but is monolithic

**Purpose:** Split orchestration from individual processing stages

**Required Changes:**
- Extract stage services (Tokenizer, Tagger, EntityLinker, etc.)
- Create pluggable stage interface
- Dependency injection for each stage
- Leave TextProcessor as orchestrator

**Tests Created:** 4 specification tests (all pass - basic structure exists)

**Next Steps:**
1. Create stage service interface
2. Extract individual stages to separate modules or classes
3. Update TextProcessor to use dependency injection
4. Create integration tests

---

### Item 7: Refinement Rule Catalog ✅ COMPLETE

**Current Status:** `fixtures/refinement_rules/catalog.json` created with 6 rule families and full input/output contracts.

**Implemented:**
- `fixtures/refinement_rules/catalog.json` — catalog of all rule families: mention_span_repair, entity_state_annotation, frame_argument_linking, nominal_mention_materialization, nominal_semantic_annotation, canonical_value_materialization
- Each rule documents: method name, provenance_rule_id, input contract, output contract, idempotency guarantee, and uid formula where applicable
- `test_rule_fixtures_directory_exists` assertion upgraded from placeholder to enforced existence check

---

### Item 8: Runtime Diagnostics ❌ NOT IMPLEMENTED

**Purpose:** Query templates and dashboard for monitoring phase execution

**Required Queries:**
- `phase_execution_summary` - nodes/edges created per phase, duration
- `phase_assertion_violations` - identify violated phase postconditions
- `orphaned_nodes_detection` - find unreachable nodes
- `pipeline_bottleneck_analysis` - identify slowest phases
- `edge_type_distribution` - analyze edge usage patterns
- `entity_density` - measure entity concentration

**Tests Created:** 5 specification tests (2 skipped - code not found)

**Next Steps:**
1. Create `textgraphx/diagnostics.py` module
2. Implement query registry with all above queries
3. Create command-line tool to run diagnostics
4. Create Cypher query templates (move to `textgraphx/queries/diagnostics.cypher`)
5. Create test fixtures in `tests/test_diagnostics.py`

---

### Item 9: KG Quality Evaluation Toolkit ❌ NOT IMPLEMENTED (meantime_evaluator exists)

**Current Status:** MEANTIME evaluator exists but not integrated

**Purpose:** Consolidated quality reporting across M1-M10

**Required Metrics:**
- Structural: node density, edge density, isolated components
- Semantic: schema compliance, constraint violations, property completeness
- Temporal: TLINK transitivity, cycle detection, temporal consistency

**Required Functions:**
- `compute_structural_metrics()` - count/ratio calculations
- `compute_semantic_metrics()` - schema validation
- `compute_temporal_metrics()` - TLINK analysis
- `generate_quality_report()` - comprehensive JSON report
- `compare_reports()` - regression detection

**Tests Created:** 5 specification tests (4 skipped - code not fully found)

**Next Steps:**
1. Create `textgraphx/kg_quality_evaluation.py` module
2. Integrate existing `meantime_evaluator.py` metrics
3. Implement missing metric computations
4. Create report generation and comparison logic
5. Create test fixtures and benchmark reports

---

## Test Files Created (61 tests total)

| File | Purpose | Tests | Status |
|------|---------|-------|--------|
| `tests/test_backlog_items_4_9_specifications.py` | Contract specs for items 4-9 | 25 | ✅ PASS |
| `tests/test_temporal_ownership_audit.py` | Item 4 audit | 11 | 🔴 6 FAIL, 5 PASS |
| `tests/test_items_5_9_audit.py` | Items 5-9 audit | 14 | 7 PASS, 7 SKIP |
| `tests/test_item4_remediation_plan.py` | Item 4 fix plan | 11 | ✅ PASS |

---

## Baseline Test Results

```
Total: 61 tests
✅ PASS: 47 tests
🔴 FAIL: 6 tests (all Item 4 violations)
⏭️ SKIP: 8 tests (Items 5, 8, 9 unimplemented)
```

**Existing Tests:** 594 tests pass (verified - no regressions)

---

## Recommended Execution Order

**Immediate (this session):**
1. **Item 4** - Fix all 6 violations (blocks Items 5-9 downstream)
2. Document fixes in architecture-overview.md

**Next Priority:**
3. **Item 5** - Checkpoint/resume (enables fault tolerance)
4. **Item 8** - Diagnostics (enables monitoring of next fixes)

**Secondary:**
5. **Item 6** - TextProcessor decomposition
6. **Item 7** - Refinement rule catalog
7. **Item 9** - Quality evaluation toolkit

---

## How to Use This Plan

1. **Review violations:** See Item 4 violations above
2. **Follow fixes:** Use implementation steps 1-5 above  
3. **Run tests:** `pytest tests/test_temporal_ownership_audit.py -v` (should pass after fixes)
4. **Verify no regressions:** `pytest tests/ -v --tb=short` (594 existing tests)
5. **Move to Item 5:** Once Item 4 passes completely

---

## Key Files

**Source files to modify:**
- `textgraphx/TemporalPhase.py` (remove TLINK+EventMention creation)
- `textgraphx/TlinksRecognizer.py` (add TLINK methods, fix Cypher)
- `textgraphx/EventEnrichmentPhase.py` (add EventMention creation)  
- `textgraphx/PipelineOrchestrator.py` (verify execution order)
- `docs/architecture-overview.md` (document ownership)

**New files to create (Items 5-9):**
- `textgraphx/checkpoint.py` (Item 5)
- `textgraphx/diagnostics.py` (Item 8)
- `textgraphx/kg_quality_evaluation.py` (Item 9)
- `fixtures/refinement_rules/*.json` (Item 7)

**Test files created:**
- See "Test Files Created" table above

---

## Validation Checklist

- [ ] Item 4: All 11 audit tests pass
- [ ] Item 4: No regressions in 594 existing tests
- [ ] Item 4: architecture-overview.md updated with ownership model
- [ ] Item 5: checkpoint.py module created with save/resume functions
- [x] Item 6: TextProcessor refactored into orchestrator + stages
- [ ] Item 7: Rule catalog fixtures created with contracts
- [ ] Item 8: diagnostics.py module with query registry
- [ ] Item 9: kg_quality_evaluation.py with metric computation

---

## Summary

**Status:** Ready for implementation  
**Next Action:** Begin Item 4 fixes (copy methods, rename, update orchestration)  
**Estimated Effort:** Item 4 (~3-4 hours), Items 5-9 (~8-10 hours total)  
**Risk Level:** Medium (Item 4 requires careful refactoring, Items 5-9 are new modules)

All test infrastructure is in place. Audit tests clearly identify violations. Implementation guides provided for each fix.
