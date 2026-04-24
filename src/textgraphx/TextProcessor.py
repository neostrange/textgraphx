"""Backward-compatibility shim for textgraphx.TextProcessor.

Canonical module: ``textgraphx.pipeline.ingestion.text_processor``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.ingestion import text_processor as _canonical

warnings.warn(
    "Importing from `textgraphx.TextProcessor` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.ingestion.text_processor` instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _canonical
