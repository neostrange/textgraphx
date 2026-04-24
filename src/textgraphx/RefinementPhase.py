"""Backward-compatibility shim for textgraphx.RefinementPhase.

Canonical module: ``textgraphx.pipeline.phases.refinement``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.phases import refinement as _canonical

warnings.warn(
    "Importing from `textgraphx.RefinementPhase` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.phases.refinement` instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _canonical
