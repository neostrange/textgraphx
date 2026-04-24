"""Backward-compatibility shim for textgraphx.TextProcessor.

Canonical module: ``textgraphx.pipeline.ingestion.text_processor``.
Importing this module emits a DeprecationWarning and re-exports
``TextProcessor`` from the canonical module.
"""

import importlib
import warnings

_canonical = importlib.import_module("textgraphx.pipeline.ingestion.text_processor")

warnings.warn(
    "Importing from `textgraphx.TextProcessor` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.ingestion.text_processor` instead.",
    DeprecationWarning,
    stacklevel=2,
)

TextProcessor = _canonical.TextProcessor

__all__ = ["TextProcessor"]
