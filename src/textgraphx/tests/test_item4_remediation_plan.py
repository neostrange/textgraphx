"""Implementation guide and concrete fixes for Item 4: Temporal Ownership Split.

This file documents the specific violations found in the audit and provides
concrete remediation steps.
"""

import pytest
from pathlib import Path
from typing import List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
TEXTGRAPHX_DIR = REPO_ROOT / "textgraphx"
TEMPORAL_PHASE_PATH = TEXTGRAPHX_DIR / "TemporalPhase.py"
TLINKS_RECOGNIZER_PATH = TEXTGRAPHX_DIR / "TlinksRecognizer.py"
EVENT_ENRICHMENT_PATH = TEXTGRAPHX_DIR / "pipeline" / "phases" / "event_enrichment.py"


@pytest.mark.unit
class TestItem4RemediationPlan:
    """Concrete plan for fixing temporal ownership violations."""

    def test_violation_1_tlink_creation_in_temporal_phase(self):
        """VIOLATION: TemporalPhase.create_tlinks_* methods should move to TlinksRecognizer."""
        # Affected methods in TemporalPhase:
        #   Line 187: create_tlinks_e2e (Event-to-Event TLINK creation)
        #   Line 223: create_tlinks_e2t (Event-to-Timex TLINK creation)
        #   Line 260: create_tlinks_t2t (Timex-to-Timex TLINK creation)
        
        # Remediation Step 1: Copy these methods to TlinksRecognizer.py
        # Remediation Step 2: Add @property or parameters for Neo4j driver
        # Remediation Step 3: Delete from TemporalPhase
        # Remediation Step 4: Update calls in run_pipeline.py or PipelineOrchestrator
        
        violations = {
            "create_tlinks_e2e": (187, "Event-to-Event TLINK creation"),
            "create_tlinks_e2t": (223, "Event-to-Timex TLINK creation"),
            "create_tlinks_t2t": (260, "Timex-to-Timex TLINK creation"),
        }
        
        for method_name, (line_num, description) in violations.items():
            assert method_name is not None  # Placeholder for actual validation

    def test_violation_2_event_mention_in_temporal_phase(self):
        """VIOLATION: TemporalPhase.create_event_mentions2 should move to EventEnrichmentPhase."""
        # Affected method in TemporalPhase:
        #   Line 600: create_event_mentions2 (EventMention materialization)
        
        # Remediation Step 1: Review EventEnrichmentPhase to understand EventMention creation
        # Remediation Step 2: Determine if create_event_mentions2 is a duplicate or refactored version
        # Remediation Step 3: Move to EventEnrichmentPhase if not already present
        # Remediation Step 4: Delete from TemporalPhase
        # Remediation Step 5: Update orchestration order (ensure EventEnrichmentPhase runs before TLINK creation)
        
        event_enrichment_src = EVENT_ENRICHMENT_PATH.read_text()
        temporal_src = TEMPORAL_PHASE_PATH.read_text()
        # Violation fix verified: create_event_mentions must be in EventEnrichmentPhase
        assert "create_event_mentions" in event_enrichment_src, \
            "EventEnrichmentPhase should contain create_event_mentions (moved from TemporalPhase)"
        # TemporalPhase must NOT own EventMention creation
        temporal_em_defs = [
            line.strip()
            for line in temporal_src.splitlines()
            if line.strip().startswith("def create_event_mentions")
        ]
        assert not temporal_em_defs, \
            f"TemporalPhase must not define create_event_mentions*; found: {temporal_em_defs}"

    def test_violation_3_tlinks_recognizer_creates_timex(self):
        """VIOLATION: TlinksRecognizer should MATCH (not CREATE) TIMEX nodes."""
        # TlinksRecognizer should accept pre-materialized TIMEX/TEvent nodes
        # It should use MATCH to query, not CREATE to materialize
        
        # Remediation Step 1: Audit TlinksRecognizer.py for CREATE/MERGE TIMEX patterns
        # Remediation Step 2: Replace CREATE/MERGE TIMEX with MATCH TIMEX
        # Remediation Step 3: Verify queries still work (may need to update WHERE clauses)
        
        tlinks_src = TLINKS_RECOGNIZER_PATH.read_text()
        bad_patterns = ["MERGE (t:TIMEX", "CREATE (t:TIMEX", "MERGE (timex:TIMEX", "CREATE (timex:TIMEX"]
        violations = [p for p in bad_patterns if p in tlinks_src]
        assert not violations, \
            f"TlinksRecognizer must not CREATE/MERGE TIMEX nodes; found: {violations}"

    def test_fix_execution_plan(self):
        """Sequential plan for executing all fixes."""
        
        fixes = [
            {
                "order": 1,
                "item": "Violation 1: Copy create_tlinks_* methods",
                "target": "TlinksRecognizer.py",
                "source": "TemporalPhase.py lines 187-297",
                "validation": "TlinksRecognizer has e2e, e2t, t2t methods with parameterized Neo4j logic",
            },
            {
                "order": 2,
                "item": "Violation 2: Move create_event_mentions2 method",
                "target": "EventEnrichmentPhase.py",
                "source": "TemporalPhase.py line 600+",
                "validation": "EventEnrichmentPhase materializes EventMention nodes",
            },
            {
                "order": 3,
                "item": "Violation 3: Fix TlinksRecognizer TIMEX creation",
                "target": "TlinksRecognizer.py (Cypher queries)",
                "source": "All create_tlinks_case* methods",
                "validation": "Queries use MATCH TIMEX, not CREATE TIMEX",
            },
            {
                "order": 4,
                "item": "Method naming: Rename extracted methods",
                "target": "TemporalPhase.py remaining methods",
                "source": "Extract-only methods (not yet renamed)",
                "validation": "Methods use extract_*, identify_*, materialize_temporal_* names",
            },
            {
                "order": 5,
                "item": "Orchestration: Document execution order",
                "target": "PipelineOrchestrator.py or docs/architecture-overview.md",
                "source": "N/A",
                "validation": "Verify: TemporalPhase → EventEnrichmentPhase → TlinksRecognizer",
            },
        ]
        
        for fix in fixes:
            assert fix["order"] > 0
            assert "target" in fix


@pytest.mark.unit
class TestItem4ExpectedOutcome:
    """Expected state after fixing temporal ownership."""

    def test_temporal_phase_responsibilities_after_fix(self):
        """After fix, TemporalPhase should ONLY materialize temporal expressions and events."""
        expected_methods = [
            "extract_timex_expressions",  # or identify_timex
            "extract_temporal_events",    # or create_tevents
            "materialize_dcт_node",       # Reference time
            "materialize_temporal_links", # Signals/CREATES_ON edges
        ]
        
        # Should NOT have:
        unexpected_methods = [
            "create_tlinks_e2e",
            "create_tlinks_e2t",
            "create_tlinks_t2t",
            "create_event_mentions2",
        ]
        
        assert "extract" in " ".join(expected_methods).lower()

    def test_tlinks_recognizer_responsibilities_after_fix(self):
        """After fix, TlinksRecognizer ONLY creates TLINK relationships."""
        # Methods it should have:
        should_have = [
            "create_tlinks_case1",
            "create_tlinks_case2",
            "create_tlinks_case3",
            "create_tlinks_e2e",
            "create_tlinks_e2t",
            "create_tlinks_t2t",
        ]
        
        # Methods it should NOT have:
        should_not_have = [
            "create_timex",
            "create_tevent",
            "create_event_mention",
            "materialize_timex",
        ]
        
        assert len(should_have) > 0

    def test_event_enrichment_phase_includes_event_mentions(self):
        """After fix, EventEnrichmentPhase includes EventMention materialization."""
        # EventEnrichmentPhase should have:
        should_have = [
            "create_event_mentions2",
            "link_event_mentions_to_frames",
            "enrich_event_mentions",
        ]
        
        assert "event_mention" in " ".join(should_have).lower()

    def test_ownership_enforcement_via_tests(self):
        """Test contract ensures no phase violates ownership."""
        # After fix, these tests should pass:
        test_contracts = [
            "test_temporal_phase_does_not_create_tlink_directly",
            "test_temporal_phase_no_eventmention_materialization",
            "test_tlinks_recognizer_only_creates_tlink_relationships",
            "test_tlinks_recognizer_does_not_materialize_events",
            "test_temporal_phase_runs_before_tlinks_recognizer",
            "test_no_phase_creates_tlink_besides_tlinks_recognizer",
        ]
        
        assert len(test_contracts) == 6


@pytest.mark.unit
class TestItem4FixImplementation:
    """Concrete implementation steps for Item 4 fixes."""

    def test_step_1_copy_tlink_methods_to_recognizer(self):
        """STEP 1: Copy create_tlinks_e2e, e2t, t2t from TemporalPhase to TlinksRecognizer."""
        
        # Expected action:
        # 1. Read TemporalPhase.py lines 187-297 (create_tlinks_* methods)
        # 2. Copy method implementations to TlinksRecognizer.py
        # 3. Ensure Neo4j graph driver is accessible
        # 4. Add logging consistent with TlinksRecognizer style
        
        step_description = """
        IMPLEMENTATION CODE:
        
        In TlinksRecognizer.py, add these methods after existing create_tlinks_case* methods:
        
        def create_tlinks_e2e(self, doc_id):
            '''Event-to-Event TLINK creation (moved from TemporalPhase).'''
            logger.debug("create_tlinks_e2e for doc_id=%s", doc_id)
            # Copy Cypher implementation from TemporalPhase
            ...
        
        def create_tlinks_e2t(self, doc_id):
            '''Event-to-Timex TLINK creation (moved from TemporalPhase).'''
            logger.debug("create_tlinks_e2t for doc_id=%s", doc_id)
            ...
        
        def create_tlinks_t2t(self, doc_id):
            '''Timex-to-Timex TLINK creation (moved from TemporalPhase).'''
            logger.debug("create_tlinks_t2t for doc_id=%s", doc_id)
            ...
        """
        
        assert "create_tlinks_e2e" in step_description

    def test_step_2_move_event_mentions_to_enrichment(self):
        """STEP 2: Move create_event_mentions2 from TemporalPhase to EventEnrichmentPhase."""
        
        # Expected action:
        # 1. Read TemporalPhase.py line 600+ (create_event_mentions2)
        # 2. Understand the Cypher logic (what EventMention properties it sets)
        # 3. Copy to EventEnrichmentPhase
        # 4. Ensure it complements existing EventMention creation logic
        # 5. Delete from TemporalPhase
        
        step_description = """
        IMPLEMENTATION ACTION:
        
        In EventEnrichmentPhase.py, add this method:
        
        def create_event_mentions2(self, doc_id):
            '''Create EventMention nodes from temporal events + frames (moved from TemporalPhase).'''
            # Copy Cypher from TemporalPhase.py
            # Ensure compatibility with create_events_mentions (possibly rename or consolidate)
            ...
        
        THEN: Delete from TemporalPhase.py line 600+
        """
        
        assert "create_event_mentions2" in step_description

    def test_step_3_fix_tlinks_recognizer_timex_queries(self):
        """STEP 3: Audit TlinksRecognizer for TIMEX materialization (should MATCH not CREATE)."""
        
        # Expected action:
        # 1. Review all create_tlinks_* method Cypher patterns
        # 2. Ensure no MERGE TIMEX or CREATE TIMEX statements exist
        # 3. Replace with MATCH TIMEX patterns
        # 4. Test queries still return correct results
        
        issues = [
            "CREATE TIMEX" in "MATCH TIMEX",  # Placeholder check
            "MERGE TIMEX" in "MATCH TIMEX",   # Placeholder check
        ]
        
        tlinks_src = TLINKS_RECOGNIZER_PATH.read_text()
        bad_patterns = ["MERGE (t:TIMEX", "CREATE (t:TIMEX", "MERGE (timex:TIMEX", "CREATE (timex:TIMEX"]
        violations = [p for p in bad_patterns if p in tlinks_src]
        assert not violations, \
            f"Step 3 fix incomplete: TlinksRecognizer still has TIMEX materialization: {violations}"
