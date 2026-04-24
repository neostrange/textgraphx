"""Compatibility wrapper for the canonical database Cypher optimizer module."""

from textgraphx.database.cypher_optimizer import (
    CypherOptimizer,
    CypherPatternOptimizer,
    QueryPerformanceContract,
    suggest_optimization_for_phase,
)

__all__ = [
    "CypherOptimizer",
    "CypherPatternOptimizer",
    "QueryPerformanceContract",
    "suggest_optimization_for_phase",
]
