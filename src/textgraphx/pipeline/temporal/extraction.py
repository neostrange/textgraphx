"""Module alias: textgraphx.pipeline.temporal.extraction -> textgraphx.pipeline.phases.temporal.

This module is a re-export shim so that ``import textgraphx.pipeline.temporal.extraction``
returns the canonical ``textgraphx.pipeline.phases.temporal`` module. Patches and
attribute lookups against this name resolve to the canonical module instance.
"""

import sys

from textgraphx.pipeline.phases import temporal as _canonical_temporal

sys.modules[__name__] = _canonical_temporal
