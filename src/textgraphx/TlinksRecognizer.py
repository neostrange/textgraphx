"""Backward-compatibility shim for textgraphx.TlinksRecognizer.

Canonical module: ``textgraphx.pipeline.phases.tlinks_recognizer``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.phases import tlinks_recognizer as _canonical
import textgraphx.pipeline.temporal.linking  # noqa: F401  (installs sys.modules alias)

warnings.warn(
    "Importing from `textgraphx.TlinksRecognizer` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.phases.tlinks_recognizer` instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _canonical
