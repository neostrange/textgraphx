"""Backward-compatibility shim for textgraphx.EventEnrichmentPhase.

Canonical module: ``textgraphx.pipeline.phases.event_enrichment``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.phases import event_enrichment as _canonical

warnings.warn(
    "Importing from `textgraphx.EventEnrichmentPhase` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.phases.event_enrichment` instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[__name__] = _canonical
