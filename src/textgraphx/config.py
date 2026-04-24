"""Compatibility alias for the canonical infrastructure config module."""

import sys
import textgraphx.infrastructure.config as _canonical_config

sys.modules[__name__] = _canonical_config
