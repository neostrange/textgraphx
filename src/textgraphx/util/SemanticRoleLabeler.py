"""Compatibility alias for the canonical semantic role labeler module."""

import sys

from textgraphx.adapters import semantic_role_labeler as _canonical_semantic_role_labeler


sys.modules[__name__] = _canonical_semantic_role_labeler
