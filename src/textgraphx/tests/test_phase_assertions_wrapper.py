"""Compatibility tests for the phase assertions module alias."""

import pytest

import textgraphx.pipeline.runtime.phase_assertions as root_phase_assertions
import textgraphx.pipeline.runtime.phase_assertions as canonical_phase_assertions


pytestmark = [pytest.mark.unit]


def test_root_phase_assertions_module_is_canonical_pipeline_runtime_module():
    assert root_phase_assertions is canonical_phase_assertions


def test_root_phase_assertions_exports_canonical_record_phase_run():
    assert root_phase_assertions.record_phase_run is canonical_phase_assertions.record_phase_run