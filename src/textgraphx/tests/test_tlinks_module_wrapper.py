"""Verify the textgraphx.TlinksRecognizer compatibility wrapper."""

import sys
import types
import warnings
from unittest.mock import MagicMock
import pytest


def test_tlinks_recognizer_module_alias(monkeypatch):
    """Ensure textgraphx.TlinksRecognizer transparently imports pipeline.phases.tlinks_recognizer."""
    
    # Store pristine sys.modules
    original_modules = dict(sys.modules)
    
    try:
        # If it was imported, remove it to force a fresh import
        if "textgraphx.pipeline.temporal.linking" in sys.modules:
            del sys.modules["textgraphx.pipeline.temporal.linking"]
        if "textgraphx.TlinksRecognizer" in sys.modules:
            del sys.modules["textgraphx.TlinksRecognizer"]
            
        import textgraphx.pipeline.phases.tlinks_recognizer as expected_module
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import textgraphx.TlinksRecognizer as legacy_module
            
            # Should have thrown DeprecationWarning
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "deprecated" in str(w[-1].message)
        
        assert hasattr(legacy_module, "TlinksRecognizer")
        assert legacy_module.TlinksRecognizer is expected_module.TlinksRecognizer
        # sys.modules routing is working
        assert sys.modules["textgraphx.pipeline.temporal.linking"] is expected_module
    finally:
        # Restore to avoid polluting later tests
        sys.modules.clear()
        sys.modules.update(original_modules)
