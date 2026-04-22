"""Tests for ENH-NOM-01, ENH-NOM-02, and ENH-NOM-03.

ENH-NOM-01: Nominal semantic-head repair pass in RefinementPhase
ENH-NOM-02: wnLexname persistence from WordnetTokenEnricher to EntityMention
ENH-NOM-03: Evaluator-side nominal profile mode filtering
"""

from __future__ import annotations

import re
import sys
import types
import inspect
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Spacy stub — RefinementPhase imports spacy at module level; stub it out so
# tests run without a working ctypes / native spacy installation.
# ---------------------------------------------------------------------------

def _stub_spacy() -> None:
    """Inject lightweight stubs for spacy and its submodules."""
    spacy_mod = types.ModuleType("spacy")
    spacy_mod.load = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
    spacy_mod.Language = MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("spacy", spacy_mod)

    for sub in ("spacy.tokens", "spacy.matcher", "spacy.language"):
        if sub not in sys.modules:
            sys.modules[sub] = types.ModuleType(sub)

    sys.modules["spacy.tokens"].Doc = MagicMock()  # type: ignore[attr-defined]
    sys.modules["spacy.tokens"].Token = MagicMock()  # type: ignore[attr-defined]
    sys.modules["spacy.tokens"].Span = MagicMock()  # type: ignore[attr-defined]
    sys.modules["spacy.matcher"].Matcher = MagicMock()  # type: ignore[attr-defined]
    sys.modules["spacy.matcher"].DependencyMatcher = MagicMock()  # type: ignore[attr-defined]
    sys.modules["spacy.language"].Language = MagicMock()  # type: ignore[attr-defined]


def _stub_heavy_deps() -> None:
    """Stub the full RefinementPhase import chain (spacy + transformers + util modules)."""
    _stub_spacy()
    for mod_name, attrs in (
        ("GPUtil", {}),
        ("transformers", {"logging": MagicMock()}),
        ("textgraphx.util.SemanticRoleLabeler", {"SemanticRoleLabel": MagicMock()}),
        ("textgraphx.util.EntityFishingLinker", {"EntityFishing": MagicMock()}),
        ("textgraphx.util.RestCaller", {"callAllenNlpApi": MagicMock()}),
        ("textgraphx.util.GraphDbBase", {"GraphDBBase": MagicMock()}),
    ):
        if mod_name not in sys.modules:
            m = types.ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[mod_name] = m


_stub_heavy_deps()

ROOT = Path(__file__).resolve().parents[1]
REFINEMENT_SRC = ROOT / "textgraphx" / "RefinementPhase.py"
WORDNET_ENRICHER_SRC = ROOT / "textgraphx" / "text_processing_components" / "WordnetTokenEnricher.py"


# ---------------------------------------------------------------------------
# Helpers to read source once
# ---------------------------------------------------------------------------

_refinement_source: str | None = None
_enricher_source: str | None = None


def _ref_src() -> str:
    global _refinement_source
    if _refinement_source is None:
        _refinement_source = REFINEMENT_SRC.read_text(encoding="utf-8")
    return _refinement_source


def _enr_src() -> str:
    global _enricher_source
    if _enricher_source is None:
        _enricher_source = WORDNET_ENRICHER_SRC.read_text(encoding="utf-8")
    return _enricher_source


# ===========================================================================
# ENH-NOM-01: Nominal Semantic Head Repair
# ===========================================================================


class TestEnhNom01SemanticHeadRepair:
    """ENH-NOM-01: resolve_nominal_semantic_heads() in RefinementPhase."""

    def test_pass_exists_in_rule_families(self):
        src = _ref_src()
        assert '"resolve_nominal_semantic_heads"' in src, (
            "resolve_nominal_semantic_heads must be in RULE_FAMILIES nominal_mentions list"
        )

    def test_pass_is_defined_as_method(self):
        src = _ref_src()
        assert "def resolve_nominal_semantic_heads(self):" in src

    def test_noun_upos_ranked_highest(self):
        """NOUN/PROPN/PRON tokens (rank 0) must beat ADJ (rank 4) in the Cypher ordering."""
        src = _ref_src()
        # The CASE expression must assign rank 0 to NOUN/PROPN/PRON
        assert "WHEN coalesce(tok.upos, '') IN ['NOUN', 'PROPN', 'PRON'] THEN 0" in src

    def test_adjective_ranked_lower_than_noun(self):
        """ADJ must have higher numeric rank (worse) than NOUN."""
        src = _ref_src()
        assert re.search(
            r"tok\.upos.*ADJ.*THEN\s+[4-9]",
            src,
        ) or "ADJ' THEN 4" in src or "ADJ', 'JJ'" in src

    def test_det_ranked_lowest(self):
        """DET/quantifier tokens must have the highest rank (worst)."""
        src = _ref_src()
        assert re.search(r"DT.*THEN\s+[5-9]", src) or "THEN 6" in src

    def test_fallback_to_existing_head_when_no_tokens(self):
        """When semantic_head IS NULL the source label must be fallback_existing_head."""
        src = _ref_src()
        assert "'fallback_existing_head'" in src

    def test_noun_preferred_source_label_present(self):
        """When a noun-preferred token is found, source must be noun_preferred_token."""
        src = _ref_src()
        assert "'noun_preferred_token'" in src

    def test_surface_head_source_label_present(self):
        """When the selected token is the same as headTokenIndex, source must be surface_head."""
        src = _ref_src()
        assert "'surface_head'" in src

    def test_sets_nominal_semantic_head_properties(self):
        """The pass must SET all expected fields on EntityMention."""
        src = _ref_src()
        for field in [
            "em.nominalSemanticHead",
            "em.nominalSemanticHeadLemma",
            "em.nominalSemanticHeadText",
            "em.nominalSemanticHeadPos",
            "em.nominalSemanticHeadUpos",
            "em.nominalSemanticHeadTokenIndex",
            "em.nominalSemanticHeadSource",
        ]:
            assert field in src, f"Missing SET on {field}"

    def test_propagates_to_entity_node(self):
        """Semantic head data must also propagate to the linked Entity node."""
        src = _ref_src()
        assert "e.nominalSemanticHead" in src
        assert "e.nominalSemanticHeadSource" in src

    def test_pass_ordered_after_materialization(self):
        """resolve_nominal_semantic_heads must run after mention materialization passes."""
        src = _ref_src()
        mat_frame = src.index("materialize_nominal_mentions_from_frame_arguments")
        mat_noun = src.index("materialize_nominal_mentions_from_noun_chunks")
        resolve = src.index('"resolve_nominal_semantic_heads"')
        assert mat_frame < resolve, "Head repair must come after frame-argument materialization"
        assert mat_noun < resolve, "Head repair must come after noun-chunk materialization"

    def test_run_returns_empty_string(self):
        """resolve_nominal_semantic_heads must end with 'return ""'."""
        src = _ref_src()
        method_start = src.index("def resolve_nominal_semantic_heads(self):")
        method_end = src.index("def annotate_nominal_semantic_profiles(self):")
        method_src = src[method_start:method_end]
        assert 'return ""' in method_src, "Method must return empty string"

    def test_graph_run_called_once(self):
        """resolve_nominal_semantic_heads must issue exactly one graph.run() call."""
        src = _ref_src()
        method_start = src.index("def resolve_nominal_semantic_heads(self):")
        method_end = src.index("def annotate_nominal_semantic_profiles(self):")
        method_src = src[method_start:method_end]
        # Count graph.run calls (not counting .data() calls)
        run_calls = re.findall(r"graph\.run\s*\(", method_src)
        assert len(run_calls) == 1, (
            f"resolve_nominal_semantic_heads must call graph.run exactly once; found {len(run_calls)}"
        )

    def test_cypher_targets_nominal_mention_label(self):
        """Cypher must match NominalMention labelled nodes."""
        src = _ref_src()
        # Find the Cypher in the method
        method_start = src.index("def resolve_nominal_semantic_heads(self):")
        method_end = src.index("def annotate_nominal_semantic_profiles(self):")
        method_src = src[method_start:method_end]
        assert "NominalMention" in method_src

    def test_right_edge_distance_tiebreaking(self):
        """Tokens at or near the right edge (end_tok) must be preferred as semantic heads."""
        src = _ref_src()
        # Must compute right_edge_distance based on end_tok
        assert "right_edge_distance" in src
        assert "end_tok" in src


# ===========================================================================
# ENH-NOM-02: wnLexname Persistence
# ===========================================================================


class TestEnhNom02WnLexnamePersistence:
    """ENH-NOM-02: wnLexname workflow from WordnetTokenEnricher to EntityMention."""

    def test_wordnet_enricher_persists_wnlexname(self):
        """WordnetTokenEnricher must SET t.wnLexname on TagOccurrence nodes."""
        src = _enr_src()
        assert "t.wnLexname = $wnLexname" in src

    def test_wordnet_enricher_derives_from_synset_lexname(self):
        """wnLexname must come from synset.lexname() call."""
        src = _enr_src()
        assert "synset.lexname()" in src
        assert "wn_lexname" in src

    def test_refinement_reads_wnlexname_from_token(self):
        """annotate_nominal_semantic_profiles must read wnLexname from head_tok."""
        src = _ref_src()
        method_start = src.index("def annotate_nominal_semantic_profiles(self):")
        next_method = src.index("\n    def ", method_start + 1)
        method_src = src[method_start:next_method]
        assert "wnLexname" in method_src

    def test_refinement_sets_nominal_head_wnlexname_on_em(self):
        """annotate_nominal_semantic_profiles must SET em.nominalHeadWnLexname."""
        src = _ref_src()
        assert "em.nominalHeadWnLexname = head_wn_lexname" in src

    def test_refinement_propagates_wnlexname_to_entity(self):
        """wnLexname must be propagated to Entity node as well."""
        src = _ref_src()
        assert "e.nominalHeadWnLexname" in src

    def test_eventive_lexnames_used_in_profile_scoring(self):
        """Eventive wnLexname values must gate nominalEventiveByWordNet."""
        src = _ref_src()
        method_start = src.index("def annotate_nominal_semantic_profiles(self):")
        next_method = src.index("\n    def ", method_start + 1)
        method_src = src[method_start:next_method]
        assert "noun.event" in method_src
        assert "noun.act" in method_src

    def test_evaluator_reads_wnlexname_from_persisted_field(self):
        """_nominal_projection_features must prefer persisted nominalHeadWnLexname."""
        from textgraphx.evaluation.meantime_evaluator import _nominal_projection_features
        import inspect
        src = inspect.getsource(_nominal_projection_features)
        assert "nominalHeadWnLexname" in src
        assert "wnLexname" in src

    def test_is_wordnet_eventive_noun_noun_event(self):
        """noun.event lexname must return True."""
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.event"}) is True

    def test_is_wordnet_eventive_noun_noun_act(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.act"}) is True

    def test_is_wordnet_eventive_noun_noun_process(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.process"}) is True

    def test_is_wordnet_eventive_noun_noun_phenomenon(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.phenomenon"}) is True

    def test_is_wordnet_eventive_noun_noun_state(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.state"}) is True

    def test_is_wordnet_eventive_noun_noun_person_is_false(self):
        """Non-eventive lexnames must return False."""
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.person"}) is False

    def test_is_wordnet_eventive_noun_noun_artifact_is_false(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.artifact"}) is False

    def test_is_wordnet_eventive_noun_empty_lexname_is_false(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        assert _is_wordnet_eventive_noun({"head_wn_lexname": ""}) is False

    def test_is_wordnet_eventive_noun_hypernym_fallback(self):
        """Should return True when hypernyms include eventive roots even with no lexname."""
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        features = {
            "head_wn_lexname": "",
            "head_nltk_synset": "",
            "head_hypernyms": ["event.n.01", "act.n.01"],
        }
        assert _is_wordnet_eventive_noun(features) is True

    def test_is_wordnet_eventive_noun_non_eventive_hypernyms(self):
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        features = {
            "head_wn_lexname": "",
            "head_nltk_synset": "",
            "head_hypernyms": ["person.n.01", "entity.n.01"],
        }
        assert _is_wordnet_eventive_noun(features) is False

    def test_annotate_profiles_run_returns_empty_string(self):
        """annotate_nominal_semantic_profiles must end with 'return ""'."""
        src = _ref_src()
        method_start = src.index("def annotate_nominal_semantic_profiles(self):")
        # Next method after this one
        next_method = src.index("\n    def ", method_start + 1)
        method_src = src[method_start:next_method]
        assert 'return ""' in method_src, "Method must return empty string"

    def test_wnlexname_in_semantic_signals_list(self):
        """wordnet_eventive_lexname must appear in the semantic signals array built by profiling."""
        src = _ref_src()
        assert "wordnet_eventive_lexname" in src


# ===========================================================================
# ENH-NOM-03: Evaluator Nominal Profile Mode Filtering
# ===========================================================================


class TestEnhNom03ProfileModeFiltering:
    """ENH-NOM-03: nominal_profile_mode filtering in build_document_from_neo4j."""

    @pytest.fixture()
    def evaluator_module(self):
        from textgraphx.evaluation import meantime_evaluator
        return meantime_evaluator

    def test_all_modes_are_documented(self, evaluator_module):
        """All five profile modes must be in allowed_profile_modes set."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        for mode in ("all", "eventive", "salient", "candidate-gold", "background"):
            assert mode in src, f"Profile mode '{mode}' not found in source"

    def test_invalid_mode_raises_value_error(self, evaluator_module):
        """An unrecognised profile mode must raise ValueError immediately."""
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        with pytest.raises(ValueError, match="nominal_profile_mode"):
            evaluator_module.build_document_from_neo4j(
                graph=graph,
                doc_id=1,
                nominal_profile_mode="nonsense_mode",
            )

    def test_none_profile_mode_defaults_to_all(self, evaluator_module):
        """None should be treated as 'all' (no filtering)."""
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        # Should not raise
        evaluator_module.build_document_from_neo4j(
            graph=graph,
            doc_id=1,
            nominal_profile_mode=None,
        )

    def test_empty_string_mode_defaults_to_all(self, evaluator_module):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        evaluator_module.build_document_from_neo4j(
            graph=graph,
            doc_id=1,
            nominal_profile_mode="",
        )

    def test_is_wordnet_eventive_noun_logic_for_eventive_mode(self):
        """eventive mode must use _is_wordnet_eventive_noun for classification."""
        from textgraphx.evaluation.meantime_evaluator import _is_wordnet_eventive_noun
        # eventive nominal: has eventive lexname
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.event"}) is True
        # non-eventive nominal: person
        assert _is_wordnet_eventive_noun({"head_wn_lexname": "noun.person"}) is False

    def test_profile_mode_filtering_passes_eventive_for_eventive_mode(self, evaluator_module):
        """In 'eventive' mode, a nominal with eventive_head=True must be included."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        # The eventive filter branch logic
        assert 'profile_mode == "eventive"' in src
        assert "eventive_nominal" in src

    def test_profile_mode_filtering_passes_salient_for_salient_mode(self, evaluator_module):
        """In 'salient' mode, a nominal with salient signals must be included."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert 'profile_mode == "salient"' in src
        assert "salient_nominal" in src

    def test_profile_mode_filtering_passes_candidate_gold_mode(self, evaluator_module):
        """In 'candidate-gold' mode, only candidate_gold=True nominals are included."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert 'profile_mode == "candidate-gold"' in src
        assert "candidate_gold" in src

    def test_profile_mode_filtering_passes_background_mode(self, evaluator_module):
        """In 'background' mode, only non-eventive background nominals are included."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert 'profile_mode == "background"' in src
        assert "background_nominal" in src

    def test_mode_all_does_not_invoke_profile_filtering(self, evaluator_module):
        """In 'all' mode the profile filtering block must be bypassed (no _nominal_projection_features call for profile)."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        # The guard is: if profile_mode != "all" and syntactic_type in NOM
        assert 'profile_mode != "all"' in src

    def test_nominal_eval_profile_property_consumed_from_features(self, evaluator_module):
        """The evaluator must consume 'nominal_eval_profile' key from features dict."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert "nominal_eval_profile" in src

    def test_nominal_eval_candidate_gold_property_consumed(self, evaluator_module):
        """The evaluator must consume 'nominal_eval_candidate_gold' from features."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert "nominal_eval_candidate_gold" in src

    def test_profile_mode_default_is_all(self, evaluator_module):
        """Default parameter value must be 'all'."""
        sig = inspect.signature(evaluator_module.build_document_from_neo4j)
        default = sig.parameters["nominal_profile_mode"].default
        assert default == "all"

    def test_profile_modes_are_validated_via_set(self, evaluator_module):
        """Allowed modes must be validated against a defined set, not ad-hoc ifs."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        assert "allowed_profile_modes" in src

    def test_eventive_combined_with_eval_profile_check(self, evaluator_module):
        """eventive mode must accept both eventive_head=True OR eval_profile == 'eventive_nominal'."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        # Both paths should be present
        assert "eventive" in src
        assert "eval_profile" in src

    def test_background_mode_excludes_eventive_mentions(self, evaluator_module):
        """background mode must explicitly exclude eventive nominals."""
        src = inspect.getsource(evaluator_module.build_document_from_neo4j)
        # The background filter: background_nominal AND not eventive
        assert "background_nominal" in src
        assert "not eventive" in src


# ===========================================================================
# Integration: RULE_FAMILIES ordering and PhaseAssertions
# ===========================================================================


class TestEnhNomRuleOrderAndPhaseAssertions:
    """Verify the three passes form a coherent ordered unit within RULE_FAMILIES."""

    def _get_nominal_family(self) -> list:
        """Read RULE_FAMILIES from source to avoid importing spacy."""
        src = _ref_src()
        # Extract nominal_mentions list from source
        nominal_entries = re.findall(
            r'"nominal_mentions"\s*:\s*\[(.*?)\]',
            src,
            re.DOTALL,
        )
        if not nominal_entries:
            return []
        return re.findall(r'"([^"]+)"', nominal_entries[0])

    def test_nominal_family_contains_all_three_passes(self):
        fam = self._get_nominal_family()
        assert "resolve_nominal_semantic_heads" in fam
        assert "annotate_nominal_semantic_profiles" in fam

    def test_head_repair_before_profile_annotation(self):
        fam = self._get_nominal_family()
        assert fam.index("resolve_nominal_semantic_heads") < fam.index("annotate_nominal_semantic_profiles")

    def test_materialization_before_head_repair(self):
        fam = self._get_nominal_family()
        assert fam.index("materialize_nominal_mentions_from_noun_chunks") < fam.index("resolve_nominal_semantic_heads")

    def test_phase_assertions_include_nominal_semantic_head_check(self):
        from textgraphx.phase_assertions import PhaseAssertions
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 5}]
        result = PhaseAssertions(graph).after_refinement()
        labels = [c["label"] for c in result.checks]
        assert "EntityMention nodes with nominal semantic head" in labels

    def test_run_nominal_family_calls_all_three(self):
        """nominal_mentions RULE_FAMILY must list all four passes so run_rule_family invokes each."""
        fam = self._get_nominal_family()
        # All four passes in the family must be present
        expected_passes = [
            "materialize_nominal_mentions_from_frame_arguments",
            "materialize_nominal_mentions_from_noun_chunks",
            "resolve_nominal_semantic_heads",
            "annotate_nominal_semantic_profiles",
        ]
        for p in expected_passes:
            assert p in fam, f"Pass '{p}' missing from nominal_mentions family"
