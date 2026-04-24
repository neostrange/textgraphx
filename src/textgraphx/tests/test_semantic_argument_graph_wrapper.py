"""Focused tests for the moved semantic argument graph helpers."""

import textgraphx.reasoning.semantic_argument_graph as legacy_semantic_argument_graph
from textgraphx.reasoning import semantic_argument_graph as canonical_semantic_argument_graph


def test_semantic_argument_graph_wrapper_reexports_canonical_symbols():
    assert legacy_semantic_argument_graph.SemanticArgumentGraph is canonical_semantic_argument_graph.SemanticArgumentGraph
    assert legacy_semantic_argument_graph.validate_graph_consistency is canonical_semantic_argument_graph.validate_graph_consistency


def test_srl_graph_constructor_builds_consistent_graph():
    graph = canonical_semantic_argument_graph.SRLGraphConstructor.build_from_srl_annotation(
        sentence_text="Alice gave Bob a book.",
        predicate="gave",
        predicate_span=(1, 1),
        roles={
            "agent": ("Alice", (0, 0)),
            "recipient": ("Bob", (2, 2)),
            "patient": ("a book", (3, 4)),
        },
    )

    is_valid, violations = canonical_semantic_argument_graph.validate_graph_consistency(graph)
    predicate_nodes = [node for node in graph.nodes.values() if node.node_type == "predicate"]

    assert is_valid is True
    assert violations == []
    assert len(predicate_nodes) == 1
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3