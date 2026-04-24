"""Backward-compatibility shim for textgraphx.GraphBasedNLP.

Canonical module: ``textgraphx.pipeline.ingestion.graph_based_nlp``.
Importing this module emits a DeprecationWarning and aliases ``sys.modules``
so that attribute lookups and patches resolve to the canonical module.
"""

import sys
import warnings

from textgraphx.pipeline.ingestion import graph_based_nlp as _canonical

warnings.warn(
    "Importing from `textgraphx.GraphBasedNLP` is deprecated. "
    "Please update your imports to use `textgraphx.pipeline.ingestion.graph_based_nlp` instead.",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> None:
    _canonical.main()


if __name__ != "__main__":
    sys.modules[__name__] = _canonical
