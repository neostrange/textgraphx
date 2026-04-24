"""Backward-compatibility shim for textgraphx.TemporalPhase.

Canonical module: ``textgraphx.pipeline.phases.temporal``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.phases import temporal as _canonical
import textgraphx.pipeline.temporal.extraction  # noqa: F401  (installs sys.modules alias)

warnings.warn(
    "Importing from `textgraphx.TemporalPhase` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.phases.temporal` instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _canonical
