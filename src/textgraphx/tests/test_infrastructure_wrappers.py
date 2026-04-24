"""Compatibility tests for infrastructure helper wrappers."""

import logging

import pytest

from textgraphx.health_check import check_neo4j_connection
from textgraphx.infrastructure.health_check import (
    check_neo4j_connection as canonical_check_neo4j_connection,
)
from textgraphx.infrastructure.logging_config import configure_logging as canonical_configure_logging
from textgraphx.infrastructure.logging_utils import debug_log, get_logger as canonical_get_logger
from textgraphx.infrastructure.performance_profiler import PhaseProfiler as canonical_phase_profiler
from textgraphx.logging_config import configure_logging
from textgraphx.logging_utils import get_logger
from textgraphx.performance_profiler import PhaseProfiler


pytestmark = [pytest.mark.unit]


def test_health_check_wrapper_reexports_canonical_helper():
    assert check_neo4j_connection is canonical_check_neo4j_connection


def test_logging_config_wrapper_reexports_canonical_helper():
    assert configure_logging is canonical_configure_logging


def test_logging_utils_wrapper_reexports_canonical_helper():
    assert get_logger is canonical_get_logger


def test_performance_profiler_wrapper_reexports_canonical_class():
    assert PhaseProfiler is canonical_phase_profiler


def test_debug_log_reports_exception_type(caplog):
    @debug_log(level=logging.DEBUG)
    def boom():
        raise ValueError("bad input")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            boom()

    assert any("ValueError" in record.message for record in caplog.records)