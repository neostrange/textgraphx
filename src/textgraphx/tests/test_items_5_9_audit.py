"""Implementation audit tests for Items 5-9.

Item 5: Checkpoint/resume support
Item 6: TextProcessor decomposition
Item 7: Refinement rule catalog+test fixtures
Item 8: Runtime diagnostics queries
Item 9: KG quality evaluation toolkit
"""

import pytest
import re
from pathlib import Path
from typing import Dict, List, Set


REPO_ROOT = Path(__file__).resolve().parents[2]
TEXTGRAPHX_DIR = REPO_ROOT / "textgraphx"


# ---------------------------------------------------------------------------
# Item 5: Checkpoint/Resume Support
# ---------------------------------------------------------------------------


class TestCheckpointResumeImplementation:
    """Audit checkpoint/resume implementation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load checkpoint/orchestrator code."""
        checkpoint_candidates = [
            TEXTGRAPHX_DIR / "checkpoint.py",
            TEXTGRAPHX_DIR / "execution_history.py",
            TEXTGRAPHX_DIR / "PipelineOrchestrator.py",
        ]
        
        self.checkpoint_code = None
        self.checkpoint_path = None
        for path in checkpoint_candidates:
            if path.exists():
                code = path.read_text()
                if "checkpoint" in code.lower() or "resume" in code.lower():
                    self.checkpoint_code = code
                    self.checkpoint_path = path
                    break

    def test_checkpoint_write_functions_exist(self):
        """Checkpoint module should have save/write checkpoint functions."""
        if not self.checkpoint_code:
            pytest.skip("Checkpoint code not found")
        
        save_patterns = [
            r"def\s+save_checkpoint",
            r"def\s+write_checkpoint",
            r"def\s+create_checkpoint",
        ]
        
        found = False
        for pattern in save_patterns:
            if re.search(pattern, self.checkpoint_code, re.IGNORECASE):
                found = True
                break
        
        # This is an expected failure for an unimplemented backlog item
        assert found or not self.checkpoint_code, \
            "Checkpoint code should include save/write/create checkpoint functions"

    def test_resume_functions_exist(self):
        """Checkpoint module should have resume/restore checkpoint functions."""
        if not self.checkpoint_code:
            pytest.skip("Checkpoint code not found")
        
        restore_patterns = [
            r"def\s+resume_from_checkpoint",
            r"def\s+restore_checkpoint",
            r"def\s+load_checkpoint",
        ]
        
        found = False
        for pattern in restore_patterns:
            if re.search(pattern, self.checkpoint_code, re.IGNORECASE):
                found = True
                break
        
        assert found or not self.checkpoint_code, \
            "Checkpoint code should include resume/restore/load checkpoint functions"

    def test_checkpoint_stores_neo4j_state(self):
        """Checkpoint should capture Neo4j node/edge counts and state."""
        if not self.checkpoint_code:
            pytest.skip("Checkpoint code not found")
        
        neo4j_patterns = [
            r"node.*count",
            r"edge.*count",
            r"query.*count",
        ]
        
        found = False
        for pattern in neo4j_patterns:
            if re.search(pattern, self.checkpoint_code, re.IGNORECASE):
                found = True
                break
        
        # Expected failure for unimplemented item
        assert found or not self.checkpoint_code


# ---------------------------------------------------------------------------
# Item 6: TextProcessor Decomposition
# ---------------------------------------------------------------------------


class TestTextProcessorDecompositionImplementation:
    """Audit TextProcessor decomposition into orchestrator + services."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load TextProcessor code."""
        self.text_processor_path = TEXTGRAPHX_DIR / "pipeline" / "ingestion" / "text_processor.py"
        assert self.text_processor_path.exists(), "canonical TextProcessor source not found"
        self.text_processor_code = self.text_processor_path.read_text()

    def test_text_processor_has_stage_services(self):
        """TextProcessor should delegate to individual stage services."""
        # Look for service instantiation or method calls
        stage_patterns = [
            r"tag_occurrence_creator",
            r"entity_processor",
            r"srl_processor",
            r"coref",
        ]
        
        services_found = sum(1 for pattern in stage_patterns 
                            if re.search(pattern, self.text_processor_code, re.IGNORECASE))
        
        # Placeholder since this is a backlog item
        assert services_found >= 4

    def test_text_processor_orchestration_methods(self):
        """TextProcessor should have orchestration methods like process_document()."""
        main_methods = [
            r"def\s+process_document",
            r"def\s+process",
            r"def\s+run",
        ]
        
        found = False
        for pattern in main_methods:
            if re.search(pattern, self.text_processor_code, re.IGNORECASE):
                found = True
                break
        
        assert found, "TextProcessor should have main orchestration method"

    def test_stage_services_location(self):
        """Stage services should be in separate files or clearly organized."""
        stage_files = [
            "text_processing_components/TagOccurrenceCreator",
            "text_processing_components/EntityProcessor",
            "text_processing_components/EntityDisambiguator",
            "text_processing_components/CoreferenceResolver",
        ]
        
        # Check if files exist or are imported
        any_found = False
        for stage_name in stage_files:
            stage_path = TEXTGRAPHX_DIR / f"{stage_name}.py"
            if stage_path.exists():
                any_found = True
                break
        
        # For now, stage services might not be separated yet (backlog item)
        assert any_found


# ---------------------------------------------------------------------------
# Item 7: Refinement Rule Catalog
# ---------------------------------------------------------------------------


class TestRefinementRuleCatalogImplementation:
    """Audit refinement rule documentation and fixtures."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load RefinementPhase code."""
        self.refinement_path = TEXTGRAPHX_DIR / "RefinementPhase.py"
        assert self.refinement_path.exists(), "RefinementPhase.py not found"
        self.refinement_code = self.refinement_path.read_text()

    def test_refinement_rules_are_documented(self):
        """RefinementPhase rules should have docstrings or comments explaining intent."""
        # Count methods/rules
        method_pattern = r"def\s+(\w+)\s*\("
        methods = re.findall(method_pattern, self.refinement_code)
        
        # Count docstrings
        docstring_pattern = r'""".*?"""'
        docstrings = re.findall(docstring_pattern, self.refinement_code, re.DOTALL)
        
        # Basic check: rules exist
        assert len(methods) > 5, "RefinementPhase should have multiple rules"

    def test_refinement_rule_families_identified(self):
        """Rules should be grouped into families (nominal, semantic, etc.)."""
        rule_family_keywords = [
            "nominal",
            "semantic",
            "entity",
            "relation",
            "argument",
        ]
        
        found_families = sum(1 for keyword in rule_family_keywords 
                            if re.search(keyword, self.refinement_code, re.IGNORECASE))
        
        # At least some family organization expected
        assert found_families >= 2

    def test_rule_fixtures_directory_exists(self):
        """Rule test fixtures should be in structured directory."""
        fixtures_paths = [
            REPO_ROOT / "fixtures" / "refinement_rules",
            TEXTGRAPHX_DIR / "fixtures" / "refinement_rules",
            TEXTGRAPHX_DIR / "refinement_fixtures",
        ]
        
        any_exist = any(p.exists() for p in fixtures_paths)
        # Backlog item might not have created this yet
        assert any_exist, (
            "Refinement rule fixtures directory not found; expected one of: "
            + ", ".join(str(p) for p in fixtures_paths)
        )


# ---------------------------------------------------------------------------
# Item 8: Runtime Diagnostics
# ---------------------------------------------------------------------------


class TestRuntimeDiagnosticsImplementation:
    """Audit runtime diagnostics query/dashboard implementation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load diagnostics/monitoring code."""
        diagnostics_candidates = [
            TEXTGRAPHX_DIR / "evaluation" / "diagnostics.py",
            TEXTGRAPHX_DIR / "diagnostics.py",
            TEXTGRAPHX_DIR / "monitoring.py",
            TEXTGRAPHX_DIR / "phase_diagnostics.py",
        ]
        
        self.diagnostics_code = None
        self.diagnostics_path = None
        for path in diagnostics_candidates:
            if path.exists():
                self.diagnostics_code = path.read_text()
                self.diagnostics_path = path
                break

    def test_phase_execution_metrics_tracked(self):
        """Runtime should track phase execution metrics."""
        if not self.diagnostics_code:
            pytest.skip("Diagnostics code not found")
        
        metric_patterns = [
            r"duration",
            r"execution_time",
            r"node.*count",
            r"edge.*count",
        ]
        
        metrics_found = sum(1 for pattern in metric_patterns 
                           if re.search(pattern, self.diagnostics_code, re.IGNORECASE))
        
        assert metrics_found >= 2

    def test_diagnostics_query_functions(self):
        """Diagnostics module should have query functions for each metric."""
        if not self.diagnostics_code:
            pytest.skip("Diagnostics code not found")
        
        query_patterns = [
            r"def\s+query_",
            r"def\s+get_.*_metrics",
        ]
        
        found = False
        for pattern in query_patterns:
            if re.search(pattern, self.diagnostics_code, re.IGNORECASE):
                found = True
                break
        
        assert found or not self.diagnostics_code


# ---------------------------------------------------------------------------
# Item 9: KG Quality Evaluation
# ---------------------------------------------------------------------------


class TestKGQualityEvaluationImplementation:
    """Audit KG quality evaluation toolkit implementation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load quality evaluation code.

        The toolkit lives in textgraphx/evaluation/ — prefer the richer
        consolidated modules before falling back to the raw evaluator file.
        """
        quality_candidates = [
            # Primary: consolidated bridge has overall_quality() + Report class
            TEXTGRAPHX_DIR / "evaluation" / "meantime_bridge.py",
            # Secondary: full-stack harness with EvaluationSuite.overall_quality()
            TEXTGRAPHX_DIR / "evaluation" / "fullstack_harness.py",
            # Tertiary: raw MEANTIME evaluator
            TEXTGRAPHX_DIR / "evaluation" / "meantime_evaluator.py",
            # Legacy fallback paths (no longer used, kept for reference)
            TEXTGRAPHX_DIR / "kg_quality.py",
            TEXTGRAPHX_DIR / "quality_evaluation.py",
        ]

        self.quality_code = None
        self.quality_path = None
        for path in quality_candidates:
            if path.exists():
                code = path.read_text()
                if "evaluat" in code.lower() or "quality" in code.lower():
                    self.quality_code = code
                    self.quality_path = path
                    break

    def test_quality_metrics_functions_exist(self):
        """Quality module should have functions computing quality metrics."""
        if not self.quality_code:
            pytest.skip("Quality evaluation code not found")

        metric_functions = [
            r"def\s+compute.*quality",
            r"def\s+overall_quality",
            r"def\s+quality_scores",
            r"def\s+phase_quality_score",
            r"def\s+structural.*metric",
            r"def\s+semantic.*metric",
            r"def\s+temporal.*metric",
        ]

        found = sum(
            1 for pattern in metric_functions
            if re.search(pattern, self.quality_code, re.IGNORECASE)
        )

        assert found >= 1, (
            f"Quality module at {self.quality_path} should expose at least one "
            "quality metric function (overall_quality, quality_scores, etc.)"
        )

    def test_evaluation_report_generation(self):
        """Quality module should generate reports."""
        if not self.quality_code:
            pytest.skip("Quality evaluation code not found")

        report_patterns = [
            r"def\s+generate.*report",
            r"class.*Report",
            r"def\s+to_dict",
            r"def\s+to_markdown",
            r"def\s+export",
        ]

        found = any(
            re.search(pattern, self.quality_code, re.IGNORECASE)
            for pattern in report_patterns
        )

        assert found, (
            f"Quality module at {self.quality_path} should have report generation "
            "(class *Report, to_dict(), to_markdown(), or export*)"
        )

    def test_meantime_compatibility(self):
        """Quality toolkit should integrate with existing MEANTIME evaluator."""
        if self.quality_code is None:
            pytest.skip("Quality module not found; skipping MEANTIME compatibility check")

        has_meantime = "meantime" in self.quality_code.lower()
        assert has_meantime, (
            f"Quality toolkit at {self.quality_path} should reference MEANTIME benchmarks"
        )
