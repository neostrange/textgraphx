"""Tests for refinement rule families (Iteration 3 item 10)."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

spacy = pytest.importorskip("spacy", reason="spaCy required for RefinementPhase import")


@pytest.mark.unit
class TestRefinementRuleFamilies:
    def _make_phase(self):
        with patch("textgraphx.neo4j_client.make_graph_from_config") as mg:
            graph = MagicMock()
            graph.run.return_value.data.return_value = []
            mg.return_value = graph
            from textgraphx.RefinementPhase import RefinementPhase
            rp = RefinementPhase(argv=[])
            rp.graph = graph
            return rp

    def test_rule_families_present(self):
        rp = self._make_phase()
        families = rp.get_rule_families()
        assert "head_assignment" in families
        assert "linking" in families
        assert "nel_correction" in families
        assert "numeric_value" in families
        assert "nominal_mentions" in families

    def test_iter_rule_names_has_values(self):
        rp = self._make_phase()
        names = [n for _, n in rp.iter_rule_names()]
        assert len(names) > 10
        assert "link_frameArgument_to_entity_via_named_entity" in names

    def test_run_rule_family_unknown_raises(self):
        rp = self._make_phase()
        with pytest.raises(ValueError):
            rp.run_rule_family("unknown")

    def test_run_rule_family_invokes_methods(self):
        rp = self._make_phase()
        # Replace methods with spies to avoid DB work.
        for name in rp.get_rule_families()["numeric_value"]:
            setattr(rp, name, MagicMock())
        rp.run_rule_family("numeric_value")
        for name in rp.get_rule_families()["numeric_value"]:
            getattr(rp, name).assert_called_once()

    def test_run_all_rule_families_invokes_all_rules(self):
        rp = self._make_phase()
        for _, name in rp.iter_rule_names():
            setattr(rp, name, MagicMock())
        rp.run_all_rule_families()
        for _, name in rp.iter_rule_names():
            getattr(rp, name).assert_called_once()


@pytest.mark.regression
def test_rule_family_sequence_stable():
    with patch("textgraphx.neo4j_client.make_graph_from_config") as mg:
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        mg.return_value = graph
        from textgraphx.RefinementPhase import RefinementPhase
        rp = RefinementPhase(argv=[])

    sequence = [name for _, name in rp.iter_rule_names()]
    # Critical passes should keep relative order.
    assert sequence.index("tag_value_entities") < sequence.index("materialize_canonical_value_nodes")
    assert sequence.index("materialize_canonical_value_nodes") < sequence.index("tag_numeric_entities")
    assert sequence.index("tag_numeric_entities") < sequence.index("detect_quantified_entities_from_frameArgument")
    assert sequence.index("link_frameArgument_to_numeric_entities") < sequence.index("detect_quantified_entities_from_frameArgument")
    assert sequence.index("detect_quantified_entities_from_frameArgument") < sequence.index("materialize_nominal_mentions_from_frame_arguments")
    assert sequence.index("materialize_nominal_mentions_from_frame_arguments") < sequence.index("materialize_nominal_mentions_from_noun_chunks")
    assert sequence.index("materialize_nominal_mentions_from_noun_chunks") < sequence.index("resolve_nominal_semantic_heads")
    assert sequence.index("resolve_nominal_semantic_heads") < sequence.index("annotate_nominal_semantic_profiles")


@pytest.mark.unit
def test_numeric_and_value_taggers_are_noop_when_flag_disabled():
    """tag_numeric_entities / tag_value_entities return "" without writing labels
    when features.fill_numeric_labels is False (the safe default)."""
    with patch("textgraphx.neo4j_client.make_graph_from_config") as mg:
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        mg.return_value = graph
        from textgraphx.RefinementPhase import RefinementPhase
        rp = RefinementPhase(argv=[])
        rp.graph = graph

    mock_flags = MagicMock()
    mock_flags.fill_numeric_labels = False
    mock_cfg = MagicMock()
    mock_cfg.features = mock_flags

    with patch("textgraphx.RefinementPhase.get_config", return_value=mock_cfg):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes an error
            assert rp.tag_numeric_entities() == ""
            assert rp.tag_value_entities() == ""
        # No DB calls should have been made
        graph.run.assert_not_called()


@pytest.mark.unit
def test_numeric_and_value_taggers_emit_deprecation_warnings_when_flag_enabled():
    """tag_numeric_entities / tag_value_entities emit DeprecationWarning when
    features.fill_numeric_labels=True (opt-in legacy mode)."""
    with patch("textgraphx.neo4j_client.make_graph_from_config") as mg:
        graph = MagicMock()
        graph.run.return_value.data.side_effect = [
            [{"tagged": 2}],
            [{"tagged": 3}],
        ]
        mg.return_value = graph
        from textgraphx.RefinementPhase import RefinementPhase
        rp = RefinementPhase(argv=[])
        rp.graph = graph

    mock_flags = MagicMock()
    mock_flags.fill_numeric_labels = True
    mock_cfg = MagicMock()
    mock_cfg.features = mock_flags

    with patch("textgraphx.RefinementPhase.get_config", return_value=mock_cfg):
        with pytest.deprecated_call(match="tag_numeric_entities"):
            rp.tag_numeric_entities()

        with pytest.deprecated_call(match="tag_value_entities"):
            rp.tag_value_entities()
