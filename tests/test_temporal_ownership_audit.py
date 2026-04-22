"""Implementation audit tests for Item 4: Temporal ownership split.

Audits to ensure clear separation between:
  - TemporalPhase: Extraction of TIMEX and TEvent nodes only
  - TlinksRecognizer: Generation of TLINK relationships only
"""

import pytest
import re
from pathlib import Path
from typing import Set, Tuple, List


REPO_ROOT = Path(__file__).parent.parent
TEXTGRAPHX_DIR = REPO_ROOT / "textgraphx"


class TestTemporalPhaseOwnershipAudit:
    """Audit TemporalPhase.py for correct extraction-only responsibility."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load source code."""
        self.temporal_phase_path = TEXTGRAPHX_DIR / "TemporalPhase.py"
        assert self.temporal_phase_path.exists(), f"Missing {self.temporal_phase_path}"
        self.temporal_code = self.temporal_phase_path.read_text()

    def test_temporal_phase_does_not_create_tlink_directly(self):
        """TemporalPhase should NOT contain any TLINK creation logic."""
        # Search for direct TLINK pattern creation
        tlink_patterns = [
            r"TLINK",  # Any mention of TLINK
            r"create.*tlink",  # create_tlink variants
            r"create.*link",  # create_link variants
        ]
        
        for pattern in tlink_patterns:
            matches = re.findall(pattern, self.temporal_code, re.IGNORECASE)
            # TLINK may appear in comments or docstrings; 
            # we're checking for actual creation logic
            cypher_matches = [m for m in matches if "TLINK {" in self.temporal_code or 
                            "MERGE.*TLINK" in self.temporal_code]
            assert len(cypher_matches) == 0, \
                f"TemporalPhase should not create TLINK edges, found: {cypher_matches}"

    def test_temporal_phase_creates_timex_and_tevent_nodes(self):
        """TemporalPhase SHOULD materialize TIMEX and TEvent nodes."""
        required_creates = {
            "TIMEX": False,
            "TEvent": False,
        }
        
        for node_type in required_creates.keys():
            # Look for Cypher patterns that create these nodes
            patterns = [
                f"CREATE.*{node_type}",
                f"MERGE.*{node_type}",
            ]
            for pattern in patterns:
                if re.search(pattern, self.temporal_code, re.IGNORECASE):
                    required_creates[node_type] = True
                    break
        
        # At least one method should create each node type
        for node_type, found in required_creates.items():
            assert found, f"TemporalPhase should create {node_type} nodes"

    def test_temporal_phase_no_eventmention_materialization(self):
        """TemporalPhase should NOT materialize EventMention nodes."""
        # EventMention materialization belongs to EventEnrichmentPhase
        event_mention_patterns = [
            r"CREATE.*EventMention",
            r"MERGE.*EventMention",
        ]
        
        for pattern in event_mention_patterns:
            matches = re.findall(pattern, self.temporal_code, re.IGNORECASE)
            assert len(matches) == 0, \
                f"TemporalPhase should not create EventMention nodes"

    def test_temporal_phase_method_names_reflect_extraction(self):
        """TemporalPhase methods should have names like 'extract', 'identify', 'materialize'."""
        # Extract method names
        method_pattern = r"def\s+(\w+)\s*\("
        methods = re.findall(method_pattern, self.temporal_code)
        
        extraction_keywords = {"extract", "identify", "materialize", "recognize_temporal", "parse"}
        phase_methods = [m for m in methods if not m.startswith("_") and m != "__init__"]
        
        # At least some methods should have extraction-related names
        extraction_methods = {m for m in phase_methods 
                             if any(kw in m.lower() for kw in extraction_keywords)}
        assert len(extraction_methods) > 0, \
            f"TemporalPhase methods should reflect extraction role, found: {phase_methods}"


class TestTlinksRecognizerOwnershipAudit:
    """Audit TlinksRecognizer.py to ensure TLINK-only responsibility."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load source code."""
        self.tlinks_path = TEXTGRAPHX_DIR / "TlinksRecognizer.py"
        if not self.tlinks_path.exists():
            # May be in a different location; search for it
            for py_file in TEXTGRAPHX_DIR.glob("**/*TLink*.py"):
                self.tlinks_path = py_file
                break
        
        assert self.tlinks_path.exists(), "Could not find TlinksRecognizer or *TLink* source file"
        self.tlinks_code = self.tlinks_path.read_text()

    def test_tlinks_recognizer_creates_tlink_relationships(self):
        """TlinksRecognizer SHOULD create TLINK relationships."""
        tlink_patterns = [
            r"CREATE.*TLINK",
            r"MERGE.*TLINK",
        ]
        
        found_tlink_creation = False
        for pattern in tlink_patterns:
            if re.search(pattern, self.tlinks_code, re.IGNORECASE):
                found_tlink_creation = True
                break
        
        assert found_tlink_creation, \
            "TlinksRecognizer should create TLINK relationships"

    def test_tlinks_recognizer_does_not_materialize_events(self):
        """TlinksRecognizer should NOT materialize TEvent or TIMEX nodes."""
        forbidden_creates = {
            "TEvent": False,
            "TIMEX": False,
        }
        
        for node_type in forbidden_creates.keys():
            patterns = [
                f"CREATE.*{node_type}",
                f"MERGE.*{node_type}",
            ]
            for pattern in patterns:
                if re.search(pattern, self.tlinks_code, re.IGNORECASE):
                    forbidden_creates[node_type] = True
                    break
        
        for node_type, found in forbidden_creates.items():
            assert not found, \
                f"TlinksRecognizer should not materialize {node_type} nodes (that's TemporalPhase's job)"

    def test_tlinks_recognizer_matches_existing_events(self):
        """TlinksRecognizer should MATCH (find) existing TEvent/TIMEX nodes, not create them."""
        # Verify it uses MATCH, not CREATE/MERGE for event/timex
        match_patterns = [
            r"MATCH.*\(.*:?TEvent",
            r"MATCH.*\(.*:?TIMEX",
        ]
        
        found_matches = False
        for pattern in match_patterns:
            if re.search(pattern, self.tlinks_code):
                found_matches = True
                break
        
        assert found_matches, \
            "TlinksRecognizer should MATCH (query) existing temporal nodes"


class TestOwnershipIntegration:
    """Integration tests verifying ownership separation in orchestration."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load orchestrator and phase code."""
        # Try multiple location patterns
        orchestrator_files = [
            TEXTGRAPHX_DIR / "PipelineOrchestrator.py",
            TEXTGRAPHX_DIR / "run_pipeline.py",
        ]
        
        self.orchestrator_code = None
        self.orchestrator_path = None
        for path in orchestrator_files:
            if path.exists():
                self.orchestrator_code = path.read_text()
                self.orchestrator_path = path
                break

    def test_temporal_phase_runs_before_tlinks_recognizer(self):
        """In pipeline execution order, TemporalPhase must run before TlinksRecognizer."""
        if not self.orchestrator_code:
            pytest.skip("Orchestrator source not found")
        
        # Find execution order
        temporal_pos = self.orchestrator_code.find("TemporalPhase")
        tlinks_pos = self.orchestrator_code.find("TlinksRecognizer")
        
        assert temporal_pos >= 0, "TemporalPhase not referenced in orchestrator"
        assert tlinks_pos >= 0, "TlinksRecognizer not referenced in orchestrator"
        assert temporal_pos < tlinks_pos, \
            "TemporalPhase must execute before TlinksRecognizer"

    def test_no_phase_creates_tlink_besides_tlinks_recognizer(self):
        """TLINK creation should be exclusive to TlinksRecognizer."""
        temporal_phase_path = TEXTGRAPHX_DIR / "TemporalPhase.py"
        refinement_phase_path = TEXTGRAPHX_DIR / "RefinementPhase.py"
        event_enrichment_path = TEXTGRAPHX_DIR / "EventEnrichmentPhase.py"
        
        phases_to_check = [
            (temporal_phase_path, "TemporalPhase"),
            (refinement_phase_path, "RefinementPhase"),
            (event_enrichment_path, "EventEnrichmentPhase"),
        ]
        
        for phase_path, phase_name in phases_to_check:
            if not phase_path.exists():
                continue
            
            code = phase_path.read_text()
            # Check for TLINK creation (not just mention)
            tlink_create = re.search(r"MERGE.*TLINK|CREATE.*TLINK", code, re.IGNORECASE)
            assert not tlink_create, \
                f"{phase_name} should not create TLINK (only TlinksRecognizer should)"


class TestOwnershipDocumentation:
    """Verify ownership documentation is in place."""

    def test_architecture_overview_documents_ownership(self):
        """architecture-overview.md should document temporal ownership split."""
        arch_path = TEXTGRAPHX_DIR.parent / "docs" / "architecture-overview.md"
        if not arch_path.exists():
            arch_path = TEXTGRAPHX_DIR / "architecture-overview.md"
        
        if arch_path.exists():
            content = arch_path.read_text()
            # Check for clarity on ownership
            assert "TemporalPhase" in content
            key_phrases = ["extraction", "TIMEX", "TEvent", "TlinksRecognizer"]
            for phrase in key_phrases:
                assert phrase in content, \
                    f"Architecture doc should mention: {phrase}"

    def test_phase_docstrings_clarify_responsibility(self):
        """TemporalPhase and TlinksRecognizer docstrings should be clear about ownership."""
        temporal_path = TEXTGRAPHX_DIR / "TemporalPhase.py"
        if temporal_path.exists():
            code = temporal_path.read_text()
            # Should mention extraction, TIMEX, TEvent
            assert "TIMEX" in code or "temporal expression" in code.lower()
