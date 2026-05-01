"""Compatibility shim — canonical module is :mod:`textgraphx.database.client`.

Re-exports the public API so legacy imports keep working.
New code should import from ``textgraphx.database.client``.
"""

from textgraphx.database.client import *  # noqa: F401,F403
from textgraphx.database.client import make_graph_from_config  # noqa: F401
