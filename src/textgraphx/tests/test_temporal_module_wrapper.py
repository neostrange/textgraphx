"""Verify the textgraphx.TemporalPhase compatibility wrapper."""

import sys
import types
import warnings
from unittest.mock import MagicMock
import pytest


def test_temporal_phase_module_alias(monkeypatch):
    """Ensure textgraphx.TemporalPhase transparently imports pipeline.phases.temporal."""
    
    # Store pristine sys.modules
    original_modules = dict(sys.modules)
    
    try:
        # If it was imported, remove it to force a fresh import
        if "textgraphx.pipeline.temporal.extraction" in sys.modules:
            del sys.modules["textgraphx.pipeline.temporal.extraction"]
        if "textgraphx.TemporalPhase" in sys.modules:
            del sys.modules["textgraphx.TemporalPhase"]
            
        import textgraphx.pipeline.phases.temporal as expected_module
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import textgraphx.TemporalPhase as legacy_module
            
            # Should have thrown DeprecationWarning
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "deprecated" in str(w[-1].message)
        
        assert hasattr(legacy_module, "TemporalPhase")
        assert legacy_module.TemporalPhase is expected_module.TemporalPhase
        # sys.modules routing is working
        assert sys.modules["textgraphx.pipeline.temporal.extraction"] is expected_module
    finally:
        # Restore to avoid polluting later tests
        sys.modules.clear()
        sys.modules.update(original_modules)
