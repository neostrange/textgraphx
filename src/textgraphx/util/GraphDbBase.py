"""Compatibility alias for the canonical graph database base module."""

import sys

from textgraphx.adapters import graph_db_base as _canonical_graph_db_base


sys.modules[__name__] = _canonical_graph_db_base
