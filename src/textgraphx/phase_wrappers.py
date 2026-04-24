"""Compatibility alias for the canonical pipeline runtime wrappers module."""

import sys
from textgraphx.pipeline.runtime import phase_wrappers as _canonical_phase_wrappers

sys.modules[__name__] = _canonical_phase_wrappers
