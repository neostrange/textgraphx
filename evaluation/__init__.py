"""Evaluation harness package (Iteration 4)."""

from .metrics import (
    GraphEvaluationHarness,
    build_quality_report,
    coverage,
    macro_average,
    precision_recall_f1,
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

__all__ = [
    "GraphEvaluationHarness",
    "build_quality_report",
    "coverage",
    "macro_average",
    "precision_recall_f1",
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
]
