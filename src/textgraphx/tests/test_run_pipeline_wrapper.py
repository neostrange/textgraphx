"""Compatibility tests for the moved pipeline runner."""

import textgraphx.orchestration.runner as legacy_run_pipeline
from textgraphx.orchestration import runner as canonical_runner


def test_run_pipeline_wrapper_reexports_canonical_main():
    assert legacy_run_pipeline.main is canonical_runner.main
