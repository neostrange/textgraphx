"""Canonical infrastructure support package for runtime helpers."""

from textgraphx.infrastructure.health_check import (
    HealthCheckError,
    check_dataset_directory,
    check_external_services,
    check_http_service,
    check_neo4j_connection,
    check_required_modules,
    check_spacy_model,
    print_health_check_report,
    run_health_checks,
)
from textgraphx.infrastructure.logging_config import configure_logging
from textgraphx.infrastructure.logging_utils import (
    ContextFilter,
    ProgressLogger,
    debug_log,
    get_logger,
    log_exception,
    log_section,
    log_subsection,
    setup_component_logging,
    timer_log,
)
from textgraphx.infrastructure.performance_profiler import (
    PhaseMetrics,
    PhaseProfiler,
    QueryMetrics,
    get_profiler,
)

__all__ = [
    "ContextFilter",
    "HealthCheckError",
    "PhaseMetrics",
    "PhaseProfiler",
    "ProgressLogger",
    "QueryMetrics",
    "check_dataset_directory",
    "check_external_services",
    "check_http_service",
    "check_neo4j_connection",
    "check_required_modules",
    "check_spacy_model",
    "configure_logging",
    "debug_log",
    "get_logger",
    "get_profiler",
    "log_exception",
    "log_section",
    "log_subsection",
    "print_health_check_report",
    "run_health_checks",
    "setup_component_logging",
    "timer_log",
]