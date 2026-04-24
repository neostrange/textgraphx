"""Compatibility wrapper for canonical semantic argument graph helpers."""

from textgraphx.reasoning.semantic_argument_graph import (
    RoleAlternationHandler,
    SRLGraphConstructor,
    SemanticArgumentGraph,
    SemanticGraphEdge,
    SemanticGraphNode,
    validate_graph_consistency,
)

__all__ = [
    "RoleAlternationHandler",
    "SRLGraphConstructor",
    "SemanticArgumentGraph",
    "SemanticGraphEdge",
    "SemanticGraphNode",
    "validate_graph_consistency",
]
