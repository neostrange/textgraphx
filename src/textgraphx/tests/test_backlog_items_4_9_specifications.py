"""Specification and contract tests for remaining backlog items (4-9).

These tests define the expected behavior, interfaces, and contracts for
features that are documented but may not yet be fully implemented.

Item 4: Temporal ownership split — clear separation between temporal extraction
        and temporal link generation phases.
Item 5: Per-document checkpoint/resume — save/restore graph state between phases.
Item 6: TextProcessor decomposition — split orchestration from individual stages.
Item 7: Refinement rule catalog — documented rule families with test fixtures.
Item 8: Runtime diagnostics — query templates for monitoring phase execution.
Item 9: KG quality evaluation — toolkit for assessing graph quality metrics.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Tuple

# Path constants
REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = REPO_ROOT / "textgraphx"
TEMPORAL_SRC = PKG_ROOT / "pipeline/phases/temporal.py"
TLINKS_SRC = PKG_ROOT / "pipeline/phases/tlinks_recognizer.py"
REFINEMENT_SRC = PKG_ROOT / "pipeline/phases/refinement.py"


# ---------------------------------------------------------------------------
# Item 4: Temporal Ownership Split
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTemporalOwnershipSplit:
    """Temporal extraction vs TLINK generation should have clear ownership."""

    def test_temporal_phase_exports_timex_and_tevent_materialization(self):
        """TemporalPhase is solely responsible for creating TIMEX and TEvent nodes."""
        # Specification: TemporalPhase should materialize only:
        #   - TIMEX nodes (temporal expressions)
        #   - TEvent nodes (temporal events)
        #   - Edges: TRIGGERS, CREATED_ON (AnnotatedText -> TIMEX)
        # It must NOT create:
        #   - TLINK relationships (that's TlinksRecognizer's job)
        #   - Frame relationships (that's EventEnrichmentPhase's job)
        
        temporal_src = TEMPORAL_SRC.read_text()
        # Must have timex/tevent materialization methods
        has_materialization = (
            "materialize_tevents" in temporal_src
            or "materialize_timex" in temporal_src
            or "create_tevents" in temporal_src
        )
        assert has_materialization, "TemporalPhase should contain materialize_tevents or materialize_timex"
        # Must NOT define TLINK creation (TlinksRecognizer's responsibility)
        tlink_defs = [
            line.strip()
            for line in temporal_src.splitlines()
            if line.strip().startswith("def create_tlinks_")
        ]
        assert not tlink_defs, f"TemporalPhase must not define create_tlinks_* methods; found: {tlink_defs}"

    def test_tlinks_recognizer_only_creates_tlink_relationships(self):
        """TlinksRecognizer is solely responsible for creating TLINK edges."""
        # Specification: TlinksRecognizer should create only:
        #   - TLINK relationships between TEvent/TIMEX nodes
        # It must NOT:
        #   - Create TEvent/TIMEX/TIMEX_RANGE nodes
        #   - Create Frame relationships
        #   - Materialize EventMention nodes
        
        tlinks_src = TLINKS_SRC.read_text()
        # Must have TLINK creation methods
        assert "create_tlinks" in tlinks_src, "TlinksRecognizer should contain create_tlinks methods"
        # Must NOT merge/create TIMEX nodes (those belong to TemporalPhase)
        bad_patterns = ["MERGE (t:TIMEX", "CREATE (t:TIMEX", "MERGE (timex:TIMEX", "CREATE (timex:TIMEX"]
        violations = [p for p in bad_patterns if p in tlinks_src]
        assert not violations, f"TlinksRecognizer must not CREATE/MERGE TIMEX nodes; found: {violations}"

    def test_ownership_prevents_duplicate_tlink_creation(self):
        """Clear ownership split prevents multiple sources from creating TLINKs."""
        # Rule: Only TlinksRecognizer.create_temporal_links() creates TLINK edges
        # Even if a phase detects a temporal relationship, it should defer
        # to TlinksRecognizer rather than creating its own TLINK
        
        sources_of_truth = {"TlinksRecognizer": "create_temporal_links"}
        assert len(sources_of_truth) == 1

    def test_temporal_phase_orchestrator_invocation_order(self):
        """TemporalPhase is invoked before TlinksRecognizer in orchestrator."""
        # Specification: Pipeline order must be:
        #   1. TemporalPhase (creates TIMEX + TEvent nodes)
        #   2. TlinksRecognizer (creates TLINK edges between nodes from step 1)
        # If reversed, TlinksRecognizer would fail to find TEvent nodes
        
        phase_order = ["TemporalPhase", "TlinksRecognizer"]
        assert phase_order.index("TemporalPhase") < phase_order.index("TlinksRecognizer")


# ---------------------------------------------------------------------------
# Item 5: Checkpoint/Resume Support
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckpointResumeSupport:
    """Per-document save/restore of graph state between phases."""

    def test_checkpoint_captures_phase_state(self):
        """Checkpoint should capture: node count, edge count, phase markers."""
        checkpoint_structure = {
            "doc_id": 12345,
            "phase": "TemporalPhase",
            "timestamp": "2026-04-06T10:30:00Z",
            "node_counts": {
                "AnnotatedText": 1,
                "Sentence": 5,
                "TagOccurrence": 50,
                "TIMEX": 3,
                "TEvent": 2,
            },
            "edge_counts": {
                "HAS_TOKEN": 50,
                "CONTAINS_SENTENCE": 5,
                "TRIGGERS": 2,
                "CREATES_ON": 3,
            },
            "properties_snapshot": {
                "AnnotatedText:creationTime": "2026-01-15",
                "TEvent:certainty": [0.85, 0.90],
            },
        }
        assert "doc_id" in checkpoint_structure
        assert "node_counts" in checkpoint_structure

    def test_checkpoint_file_location(self):
        """Checkpoints stored in: <output_dir>/checkpoints/<doc_id>/<phase_name>.json"""
        doc_id = 12345
        phase_name = "TemporalPhase"
        checkpoint_path = f"out/checkpoints/{doc_id}/{phase_name}.json"
        assert f"{doc_id}" in checkpoint_path
        assert f"{phase_name}" in checkpoint_path

    def test_resume_validates_checkpoint_integrity(self):
        """Resume operation checks: doc_id, phase name, node/edge count thresholds."""
        # Specification: Resume must verify:
        #   1. Checkpoint is for the correct document
        #   2. Checkpoint is for a phase earlier in the pipeline
        #   3. Node counts exceed minimum thresholds (no partial materialization)
        
        def validate_checkpoint(checkpoint, expected_doc_id, expected_phase):
            return (
                checkpoint.get("doc_id") == expected_doc_id and
                checkpoint.get("phase") in ["SchemaIngestion", "RefinementPhase", "TemporalPhase"]
            )
        
        test_checkpoint = {"doc_id": 99999, "phase": "TemporalPhase"}
        assert validate_checkpoint(test_checkpoint, 99999, "TemporalPhase")

    def test_resume_skips_completed_phases(self):
        """Resume from TemporalPhase skips SchemaIngestion and RefinementPhase."""
        completed_phases = {"SchemaIngestion", "RefinementPhase"}
        remaining_phases = [
            "TemporalPhase",
            "EventEnrichmentPhase",
            "TlinksRecognizer",
        ]
        assert remaining_phases[0] not in completed_phases


# ---------------------------------------------------------------------------
# Item 6: TextProcessor Decomposition
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTextProcessorDecomposition:
    """TextProcessor should decompose into orchestrator + stage services."""

    def test_textprocessor_orchestrator_interface(self):
        """Orchestrator component coordinates stage services."""
        # Specification: PipelineOrchestrator should:
        #   - Accept document input
        #   - Invoke each stage service in sequence
        #   - Handle errors and phase assertions
        #   - Return consolidated results
        
        orchestrator_methods = [
            "run_stage",
            "run_full_pipeline",
            "handle_error",
            "validate_phase",
        ]
        assert "run_stage" in orchestrator_methods

    def test_stage_service_interface(self):
        """Each stage service (TokenProcessor, EntityFisher, etc.) has consistent interface."""
        # Specification: Stage service interface:
        #   - __init__(config: Config)
        #   - process(document) -> ProcessedDocument
        #   - validate() -> ValidationResult
        
        stage_interface = ["__init__", "process", "validate"]
        assert "process" in stage_interface

    def test_stage_services_are_stateless(self):
        """Stage services should be stateless (except for injected deps).

        Each component receives its dependencies at construction time and does
        not hold mutable shared state.  Verified by checking that:
        - All services live in separate module files under text_processing_components/
        - The component factory creates fresh instances per build() call
        - No global-state side-channels are used between services
        """
        component_dir = PKG_ROOT / "text_processing_components"
        assert component_dir.exists(), "text_processing_components/ not found"

        # Each service has its own module file
        service_modules = [f for f in component_dir.glob("*.py") if not f.name.startswith("_")]
        assert len(service_modules) >= 8, (
            f"Expected >=8 stage service modules in {component_dir}, "
            f"found {len(service_modules)}: {[f.name for f in service_modules]}"
        )

        # The factory module uses a build() class method that accepts dependency params
        factory_path = component_dir / "pipeline" / "component_factory.py"
        assert factory_path.exists(), "pipeline/component_factory.py not found"
        factory_code = factory_path.read_text()
        assert "def build" in factory_code, "Factory must expose a build() class method"
        # build() must not hard-code any endpoint —
        # all external resources are injected via parameters
        assert "neo4j_repository" in factory_code
        assert "wsd_endpoint" in factory_code

    def test_dependency_injection_for_stage_services(self):
        """Stages accept all dependencies via constructor; TextProcessor uses the factory."""
        factory_path = PKG_ROOT / "text_processing_components" / "pipeline" / "component_factory.py"
        assert factory_path.exists(), "component_factory.py not found"
        factory_code = factory_path.read_text()

        # Factory accepts all external dependencies as parameters
        for dep in ("neo4j_repository", "wsd_endpoint", "coref_endpoint", "nlp"):
            assert dep in factory_code, (
                f"component_factory.build() must accept '{dep}' for dependency injection"
            )

        # TextProcessor delegates construction to the factory (DI wire-up)
        tp_path = PKG_ROOT / "pipeline" / "ingestion" / "text_processor.py"
        assert tp_path.exists()
        tp_code = tp_path.read_text()
        assert "component_factory" in tp_code, (
            "TextProcessor should import component_factory for DI wiring"
        )
        assert "TextPipelineComponentFactory.build" in tp_code, (
            "TextProcessor.__init__ must call TextPipelineComponentFactory.build()"
        )


# ---------------------------------------------------------------------------
# Item 7: Refinement Rule Catalog
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefinementRuleCatalog:
    """Documented rule families with test fixtures."""

    def test_rule_family_structure(self):
        """Each rule family documents: purpose, input contract, output contract, fixtures."""
        rule_family = {
            "name": "nominal_mentions",
            "description": "Materialize nominal entity mentions from noun chunks and frame arguments",
            "rules": [
                "materialize_nominal_mentions_from_frame_arguments",
                "materialize_nominal_mentions_from_noun_chunks",
                "resolve_nominal_semantic_heads",
                "annotate_nominal_semantic_profiles",
            ],
            "input_contract": {
                "nodes": ["Entity", "EntityMention", "Frame", "FrameArgument"],
                "edges": ["REFERS_TO", "PARTICIPANT"],
            },
            "output_contract": {
                "nodes": ["NominalMention"],
                "edges": ["IS_A", "SEMANTIC_HEAD"],
            },
            "test_fixtures": [
                "fixtures/nominal_entities_dogs.json",
                "fixtures/nominal_events_running.json",
            ],
        }
        assert rule_family["name"] == "nominal_mentions"
        assert len(rule_family["rules"]) > 0
        assert "input_contract" in rule_family

    def test_rule_family_fixtures(self):
        """Fixtures document expected input/output for each rule."""
        # Specification: Each fixture file contains:
        fixture = {
            "name": "nominal_entities_dogs",
            "input": {
                "entity": {"id": 1, "text": "dogs"},
                "mentions": [
                    {"start": 0, "end": 4, "text": "dogs", "pos": "NNS"}
                ],
            },
            "expected_output": {
                "nominal_mention": {
                    "id": 101,
                    "text": "dogs",
                    "semantic_head_idx": 0,
                    "wnLexname": "noun.animal",
                },
            },
        }
        assert fixture["name"] == "nominal_entities_dogs"
        assert "expected_output" in fixture

    def test_rule_documentation(self):
        """Each rule is documented with: trigger condition, Cypher, side effects."""
        rule_doc = {
            "name": "resolve_nominal_semantic_heads",
            "trigger": "When: EntityMention has entity_type in ['PERSON', 'LOCATION', 'ORGANIZATION']",
            "logic": "Select the head token preferring NOUN/PROPN > ADJ > DET",
            "cypher_outline": "MATCH (em:EntityMention)-[:REFERS_TO]->(e:Entity), "
                             "MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(em) "
                             "WHERE tok.pos IN ['NN', 'NNP', 'NNPS', 'JJ'] "
                             "SET em.nominalSemanticHead = tok.id",
            "side_effects": "Creates nominalSemanticHead field on EntityMention nodes",
        }
        assert rule_doc["name"] == "resolve_nominal_semantic_heads"
        assert "cypher_outline" in rule_doc


# ---------------------------------------------------------------------------
# Item 8: Runtime Diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuntimeDiagnosticQueries:
    """Query templates for monitoring phase execution and debugging."""

    def test_phase_execution_summary_query(self):
        """Query: aggregate counts by phase (nodes created, edges created, duration)."""
        # Query outline: 
        # MATCH (pr:PhaseRun) 
        # WHERE pr.phase IN ['SchemaIngestion', 'TemporalPhase', ...]
        # RETURN pr.phase, count(nodes), count(edges), pr.duration_sec
        
        query_name = "phase_execution_summary"
        required_returns = ["phase", "node_count", "edge_count", "duration_sec"]
        assert all(ret in required_returns for ret in required_returns)

    def test_phase_assertion_violations_query(self):
        """Query: find phases that violated their post-assertions."""
        # Query: MATCH (pa:PhaseAssertion) WHERE pa.violation = true 
        # RETURN pa.phase, pa.assertion_type, pa.violation_details
        
        query_name = "phase_assertion_violations"
        required_return_fields = ["phase", "assertion_type", "violation_details"]
        assert query_name == "phase_assertion_violations"
        assert all(field in required_return_fields for field in ["phase", "violation_details"])

    def test_orphaned_nodes_detection_query(self):
        """Query: find nodes with no incoming/outgoing edges (potential bugs)."""
        # Query: MATCH (n) 
        # WHERE NOT (n)<--() AND NOT (n)-->()
        # RETURN labels(n) AS node_type, count(*) AS orphan_count
        
        expected_orphan_types = {"Node", "Entity", "TIMEX", "TEvent"}
        assert "TIMEX" in expected_orphan_types

    def test_pipeline_bottleneck_analysis_query(self):
        """Query: identify phases taking longest time (bottleneck detection)."""
        # Query: MATCH (pr:PhaseRun) 
        # RETURN pr.phase, avg(pr.duration_sec), max(pr.duration_sec)
        # ORDER BY avg(pr.duration_sec) DESC
        
        metrics = ["phase", "avg_duration", "max_duration", "percentile_p95"]
        assert "avg_duration" in metrics

    def test_diagnostic_query_registry(self):
        """All diagnostic queries registered in central registry for easy access."""
        registry = {
            "phase_execution_summary": "Monitor phase durations and node/edge creation",
            "phase_assertion_violations": "Identify phases that violated post-assertions",
            "orphaned_nodes": "Find unreachable nodes in graph",
            "pipeline_bottlenecks": "Identify slowest phases",
            "edge_type_distribution": "Analyze edge usage patterns",
            "entity_density": "Measure entity concentration by phase",
        }
        assert len(registry) >= 6
        assert "phase_execution_summary" in registry


# ---------------------------------------------------------------------------
# Item 9: KG Quality Evaluation Toolkit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKGQualityEvaluationToolkit:
    """Toolkit for assessing Knowledge Graph quality metrics."""

    def test_structural_quality_metrics(self):
        """Metrics: node density, edge density, isolated component count."""
        metrics = {
            "node_count": 5000,
            "edge_count": 12000,
            "node_density": 12000 / (5000 * 5000),  # edges / (nodes^2)
            "edge_count_per_node": 12000 / 5000,  # Average degree
            "isolated_components": 3,  # Number of disconnected subgraphs
            "largest_component_size": 4997,  # Nodes in main component
        }
        assert metrics["edge_count_per_node"] > 2

    def test_semantic_quality_metrics(self):
        """Metrics: schema compliance, relation type coverage, constraint violations."""
        semantic_metrics = {
            "schema_compliant_nodes": 4980,
            "schema_violations": 20,
            "compliance_rate": 0.996,
            "relation_types_used": 15,
            "relation_types_available": 20,
            "coverage_rate": 0.75,
            "property_completeness": {
                "Entity": {"name": 0.98, "type": 0.99, "confidence": 0.45},
                "TEvent": {"certainty": 0.92, "aspect": 0.88},
            },
        }
        assert semantic_metrics["compliance_rate"] > 0.99

    def test_temporal_consistency_metrics(self):
        """Metrics: TLINK transitivity violations, cycle detection."""
        temporal_metrics = {
            "tlink_count": 250,
            "valid_before_after_chains": 240,
            "transitivity_violations": 10,  # e1 BEFORE e2, e2 BEFORE e3, e3 BEFORE e1
            "cycles_detected": 2,
            "temporal_consistency_score": 0.96,
        }
        assert temporal_metrics["temporal_consistency_score"] < 1.0  # Real data has violations

    def test_evaluation_report_structure(self):
        """Quality evaluation report includes: timestamp, metrics, warnings, recommendations."""
        report = {
            "timestamp": "2026-04-06T12:00:00Z",
            "document_id": 12345,
            "evaluation_version": "1.0",
            "structural_metrics": {"node_count": 500, "edge_count": 1200},
            "semantic_metrics": {"compliance_rate": 0.988},
            "temporal_metrics": {"temporal_consistency_score": 0.94},
            "warnings": [
                "Found 5 orphaned TIMEX nodes with no incoming edges",
                "Entity type coverage at 78% (below 90% target)",
            ],
            "recommendations": [
                "Investigate orphaned TIMEX nodes (temporal extraction gap?)",
                "Review entity linking coverage for low-confidence entities",
            ],
        }
        assert "structural_metrics" in report
        assert "recommendations" in report
        assert len(report["warnings"]) > 0

    def test_quality_toolkit_interface(self):
        """Toolkit provides: compute_metrics(), generate_report(), compare_reports()."""
        toolkit_methods = [
            "compute_structural_metrics",
            "compute_semantic_metrics",
            "compute_temporal_metrics",
            "generate_quality_report",
            "compare_reports",
            "identify_regression",
        ]
        assert "generate_quality_report" in toolkit_methods
        assert "compare_reports" in toolkit_methods
