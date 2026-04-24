"""Compatibility wrapper for the canonical infrastructure health-check module."""

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

__all__ = [
    "HealthCheckError",
    "check_dataset_directory",
    "check_external_services",
    "check_http_service",
    "check_neo4j_connection",
    "check_required_modules",
    "check_spacy_model",
    "print_health_check_report",
    "run_health_checks",
]
