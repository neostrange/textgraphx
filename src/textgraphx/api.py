"""Compatibility alias for the canonical infrastructure API module."""

import sys

from textgraphx.infrastructure import api as _canonical_api

sys.modules[__name__] = _canonical_api
