"""Evaluation harness package (Iteration 4).

Core modules:
  - metrics: GraphEvaluationHarness, macro metrics (precision, recall, f1)
  - meantime_evaluator: Document-level and aggregate evaluation
  - report_validity: Unified validity headers and metadata tracking
  - determinism: Reproducibility verification via run comparison
  - unified_metrics: Standardized metric containers with validity headers
  - integration: Runners and adapters for certified evaluation reports
  - mention_layer_evaluator: Mention layer phase evaluation
  - edge_semantics_evaluator: Edge semantics phase evaluation
  - phase_assertion_evaluator: Phase contract validation
  - semantic_category_evaluator: Semantic categorization evaluation
  - legacy_layer_evaluator: Legacy data preservation evaluation
  - fullstack_harness: End-to-end orchestrator for all phases
  - meantime_bridge: M8a - Integration with MEANTIME gold-standard evaluation
  - cross_phase_validator: M8b - Cross-phase semantic coherence validation
"""

from .ci_integration import (
    CIReportGenerator,
    LocalPrecommitChecker,
    QualityGateConfig,
    QualityGateResult,
    QualityGateVerifierCI,
    QualityTrendTracker,
)
from .cross_phase_validator import (
    ConsistencyReport,
    CrossPhaseValidator,
    PhaseInvariantViolation,
    ViolationSeverity,
)
from .determinism import (
    DeterminismReport,
    DeterminismViolation,
    compare_metric_results,
)
from .edge_semantics_evaluator import (
    EdgeSemanticsEvaluator,
    create_edge_semantics_report,
)
from .fullstack_harness import (
    EvaluationSuite,
    FullStackEvaluator,
    compare_evaluation_suites,
)
from .meantime_bridge import (
    ConsolidatedQualityReport,
    EvalBridge,
    LayerScores,
    MEANTIMEBridge,
    MEANTIMEResults,
    QualityReport,
)
from .regression_detector import (
    BaselineManager,
    BaselineMetrics,
    QualityGateVerifier,
    RegressionAnalysis,
    RegressionDetector,
    VarianceAnalyzer,
    VarianceReport,
)
from .integration import (
    StandardizedEvaluationRunner,
    compare_runs_for_determinism,
    load_evaluation_report,
)
from .legacy_layer_evaluator import (
    LegacyLayerEvaluator,
    create_legacy_layer_report,
)
from .meantime_evaluator import (
    EvaluationMapping,
    aggregate_reports,
    build_document_from_neo4j,
    build_dataset_diagnostics,
    build_document_diagnostics,
    evaluate_documents,
    flatten_aggregate_rows_for_csv,
    flatten_report_rows_for_csv,
    parse_meantime_xml,
    render_markdown_report,
)
from .mention_layer_evaluator import (
    MentionLayerEvaluator,
    create_mention_layer_report,
)
from .metrics import (
    GraphEvaluationHarness,
    build_quality_report,
    coverage,
    macro_average,
    precision_recall_f1,
)
from .phase_assertion_evaluator import (
    PhaseAssertionEvaluator,
    create_phase_assertion_report,
)
from .report_validity import (
    RunMetadata,
    ValidityHeader,
    check_fusion_activation,
    compute_config_hash,
    compute_dataset_hash,
    render_validity_header_json,
    render_validity_header_yaml,
)
from .semantic_category_evaluator import (
    SemanticCategoryEvaluator,
    create_semantic_category_report,
)
from .unified_metrics import (
    UnifiedMetricReport,
    create_unified_report,
)

__all__ = [
    # Metrics and harness
    "GraphEvaluationHarness",
    "build_quality_report",
    "coverage",
    "macro_average",
    "precision_recall_f1",
    # MeanTime evaluator
    "parse_meantime_xml",
    "build_document_from_neo4j",
    "evaluate_documents",
    "aggregate_reports",
    "EvaluationMapping",
    "build_document_diagnostics",
    "build_dataset_diagnostics",
    "flatten_report_rows_for_csv",
    "flatten_aggregate_rows_for_csv",
    "render_markdown_report",
    # M8a - MEANTIME Bridge
    "MEANTIMEBridge",
    "EvalBridge",
    "MEANTIMEResults",
    "ConsolidatedQualityReport",
    "QualityReport",
    "LayerScores",
    # M8b - Cross-Phase Validator
    "CrossPhaseValidator",
    "ConsistencyReport",
    "PhaseInvariantViolation",
    "ViolationSeverity",
    # M9 - Regression Detection
    "BaselineManager",
    "BaselineMetrics",
    "RegressionDetector",
    "RegressionAnalysis",
    "VarianceAnalyzer",
    "VarianceReport",
    "QualityGateVerifier",
    # M10 - CI/CD Integration
    "QualityGateConfig",
    "QualityGateResult",
    "QualityGateVerifierCI",
    "CIReportGenerator",
    "QualityTrendTracker",
    "LocalPrecommitChecker",
    # Validity headers and metadata
    "RunMetadata",
    "ValidityHeader",
    "compute_dataset_hash",
    "compute_config_hash",
    "check_fusion_activation",
    "render_validity_header_yaml",
    "render_validity_header_json",
    # Determinism checking
    "DeterminismViolation",
    "DeterminismReport",
    "compare_metric_results",
    # Unified metrics
    "UnifiedMetricReport",
    "create_unified_report",
    # Integration
    "StandardizedEvaluationRunner",
    "compare_runs_for_determinism",
    "load_evaluation_report",
    # Phase evaluators
    "MentionLayerEvaluator",
    "create_mention_layer_report",
    "EdgeSemanticsEvaluator",
    "create_edge_semantics_report",
    "PhaseAssertionEvaluator",
    "create_phase_assertion_report",
    "SemanticCategoryEvaluator",
    "create_semantic_category_report",
    "LegacyLayerEvaluator",
    "create_legacy_layer_report",
    # Full-stack harness
    "EvaluationSuite",
    "FullStackEvaluator",
    "compare_evaluation_suites",
]
