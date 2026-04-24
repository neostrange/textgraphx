"""Compatibility alias for the canonical ingestion TextProcessor module."""

import sys

from textgraphx.pipeline.ingestion import text_processor as _canonical_text_processor

sys.modules[__name__] = _canonical_text_processor
