"""Canonical database support package for client and query helpers."""

from textgraphx.database.client import (
    BoltGraphCompat,
    get_config_section,
    make_bolt_driver_from_config,
    make_graph_from_config,
)
from textgraphx.database.cypher_optimizer import (
    CypherOptimizer,
    CypherPatternOptimizer,
    QueryPerformanceContract,
    suggest_optimization_for_phase,
)

__all__ = [
    "BoltGraphCompat",
    "CypherOptimizer",
    "CypherPatternOptimizer",
    "QueryPerformanceContract",
    "get_config_section",
    "make_bolt_driver_from_config",
    "make_graph_from_config",
    "suggest_optimization_for_phase",
]