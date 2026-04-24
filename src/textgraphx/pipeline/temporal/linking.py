"""Module alias: textgraphx.pipeline.temporal.linking -> textgraphx.pipeline.phases.tlinks_recognizer.

This module is a re-export shim so that ``import textgraphx.pipeline.temporal.linking``
returns the canonical ``textgraphx.pipeline.phases.tlinks_recognizer`` module.
"""

import sys

from textgraphx.pipeline.phases import tlinks_recognizer as _canonical_tlinks

sys.modules[__name__] = _canonical_tlinks
