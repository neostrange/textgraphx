import pytest

try:
    from textgraphx.text_processing_components.WordnetTokenEnricher import WordnetTokenEnricher
except Exception as exc:  # pragma: no cover - environment-dependent dependency guard
    pytest.skip(f"WordNet enricher deps unavailable: {exc}", allow_module_level=True)


class _FakeRelatedLemma:
    def __init__(self, name, synset):
        self._name = name
        self._synset = synset

    def name(self):
        return self._name

    def synset(self):
        return self._synset


class _FakeLemma:
    def __init__(self, related):
        self._related = related

    def derivationally_related_forms(self):
        return self._related


class _FakeSynset:
    def __init__(self, name, pos, min_depth=0, max_depth=0, entails=None, causes=None, lemmas=None):
        self._name = name
        self._pos = pos
        self._min_depth = min_depth
        self._max_depth = max_depth
        self._entails = entails or []
        self._causes = causes or []
        self._lemmas = lemmas or []

    def name(self):
        return self._name

    def pos(self):
        return self._pos

    def min_depth(self):
        return self._min_depth

    def max_depth(self):
        return self._max_depth

    def entailments(self):
        return self._entails

    def causes(self):
        return self._causes

    def lemmas(self):
        return self._lemmas


def _make_enricher():
    return WordnetTokenEnricher(neo4j_executor=None)


def test_derivational_features_extract_eventive_verbs():
    verb_rel = _FakeRelatedLemma("decide", _FakeSynset("decide.v.01", "v"))
    noun_rel = _FakeRelatedLemma("decision", _FakeSynset("decision.n.01", "n"))
    source = _FakeSynset("decision.n.01", "n", lemmas=[_FakeLemma([verb_rel, noun_rel])])

    forms, eventive_verbs = _make_enricher().get_derivational_features(source, token_lemma="decision")

    assert "decide" in forms
    assert "decision" in forms
    assert "decide.v.01" in eventive_verbs
    assert "decision.n.01" not in eventive_verbs


def test_derivational_features_filter_lexically_distant_eventive_verbs():
    close_rel = _FakeRelatedLemma("withdraw", _FakeSynset("withdraw.v.09", "v"))
    noisy_rel = _FakeRelatedLemma("queer", _FakeSynset("queer.v.02", "v"))
    source = _FakeSynset("withdrawal.n.02", "n", lemmas=[_FakeLemma([close_rel, noisy_rel])])

    _, eventive_verbs = _make_enricher().get_derivational_features(source, token_lemma="withdrawal")

    assert "withdraw.v.09" in eventive_verbs
    assert "queer.v.02" not in eventive_verbs


def test_verb_relation_features_extract_entails_and_causes():
    entails_syn = _FakeSynset("snore.v.01", "v")
    causes_syn = _FakeSynset("kill.v.01", "v")
    source = _FakeSynset("sleep.v.01", "v", entails=[entails_syn], causes=[causes_syn])

    entails, causes = _make_enricher().get_verb_relation_features(source)

    assert entails == ["snore.v.01"]
    assert causes == ["kill.v.01"]


def test_depth_features_produce_bounded_abstraction_score():
    source = _FakeSynset("institution.n.01", "n", min_depth=2, max_depth=8)

    depth_min, depth_max, abstraction = _make_enricher().get_depth_features(source)

    assert depth_min == 2
    assert depth_max == 8
    assert 0.0 <= abstraction <= 1.0
    assert abstraction == 0.6


def test_depth_features_handles_zero_depth_safely():
    source = _FakeSynset("entity.n.01", "n", min_depth=0, max_depth=0)

    depth_min, depth_max, abstraction = _make_enricher().get_depth_features(source)

    assert depth_min == 0
    assert depth_max == 0
    assert abstraction == 0.0
