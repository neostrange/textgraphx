"""Phase F — SRL throughput & reliability tests.

Covers:
- _LruCache: basic get/set, LRU eviction, per-URL key isolation
- _CircuitBreaker: open after threshold failures, cooldown reset, success reset
- callAllenNlpApi: cache hit bypasses requests, circuit-breaker blocks call,
  successful response populates cache, failure records circuit-breaker
- callNominalSrlApi: unconfigured URL returns {}, cache hit, circuit open
- callNominalSrlApiBatch: returns list, empty when no URL, cache satisfaction,
  concurrent async path
- callAllenNlpApiBatch: list return, circuit open short-circuits all
- graph_based_nlp wiring: nominal SRL loop uses batch call
"""

import asyncio
import importlib
import time
import types
import unittest.mock as mock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(srl_url="http://srl:8010/predict", nom_srl_url="http://nom:8011/predict_nom", timeout=5):
    cfg = types.SimpleNamespace(
        services=types.SimpleNamespace(
            srl_url=srl_url,
            nom_srl_url=nom_srl_url,
            service_timeout_sec=timeout,
        )
    )
    return cfg


def _fresh_module():
    """Re-import rest_caller to get a fresh module with clean module globals."""
    import textgraphx.adapters.rest_caller as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# _LruCache tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_lru_cache__miss_returns_none():
    from textgraphx.adapters.rest_caller import _LruCache
    c = _LruCache(maxsize=10)
    assert c.get("http://svc", "hello") is None


@pytest.mark.unit
def test_lru_cache__set_then_get_returns_value():
    from textgraphx.adapters.rest_caller import _LruCache
    c = _LruCache(maxsize=10)
    c.set("http://svc", "hello", {"verbs": []})
    assert c.get("http://svc", "hello") == {"verbs": []}


@pytest.mark.unit
def test_lru_cache__different_urls_isolated():
    from textgraphx.adapters.rest_caller import _LruCache
    c = _LruCache(maxsize=10)
    c.set("http://a", "sent", {"id": "a"})
    c.set("http://b", "sent", {"id": "b"})
    assert c.get("http://a", "sent") == {"id": "a"}
    assert c.get("http://b", "sent") == {"id": "b"}


@pytest.mark.unit
def test_lru_cache__evicts_oldest_when_full():
    from textgraphx.adapters.rest_caller import _LruCache
    c = _LruCache(maxsize=3)
    for i in range(3):
        c.set("http://svc", f"sent{i}", {"i": i})
    # Access sent0 so it becomes most-recently-used
    c.get("http://svc", "sent0")
    # Add a fourth entry — sent1 (oldest unaccessed) should be evicted
    c.set("http://svc", "sent3", {"i": 3})
    assert c.get("http://svc", "sent1") is None
    assert c.get("http://svc", "sent0") is not None
    assert c.get("http://svc", "sent3") is not None


@pytest.mark.unit
def test_lru_cache__update_existing_key_no_growth():
    from textgraphx.adapters.rest_caller import _LruCache
    c = _LruCache(maxsize=5)
    c.set("http://svc", "sent", {"v": 1})
    c.set("http://svc", "sent", {"v": 2})
    assert len(c._store) == 1
    assert c.get("http://svc", "sent") == {"v": 2}


# ---------------------------------------------------------------------------
# _CircuitBreaker tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_circuit_breaker__closed_initially():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=5, cooldown=30)
    assert not cb.is_open("http://svc")


@pytest.mark.unit
def test_circuit_breaker__opens_after_threshold_failures():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=5, cooldown=30)
    for _ in range(5):
        cb.record_failure("http://svc")
    assert cb.is_open("http://svc")


@pytest.mark.unit
def test_circuit_breaker__does_not_open_before_threshold():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=5, cooldown=30)
    for _ in range(4):
        cb.record_failure("http://svc")
    assert not cb.is_open("http://svc")


@pytest.mark.unit
def test_circuit_breaker__success_resets_failures():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=5, cooldown=30)
    for _ in range(4):
        cb.record_failure("http://svc")
    cb.record_success("http://svc")
    for _ in range(4):
        cb.record_failure("http://svc")
    assert not cb.is_open("http://svc")


@pytest.mark.unit
def test_circuit_breaker__resets_after_cooldown():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=2, cooldown=1)
    cb.record_failure("http://svc")
    cb.record_failure("http://svc")
    assert cb.is_open("http://svc")
    # Simulate time advancing past cooldown by setting backoff_until to the past
    cb._backoff_until["http://svc"] = time.monotonic() - 1.0
    assert not cb.is_open("http://svc")


@pytest.mark.unit
def test_circuit_breaker__isolated_per_url():
    from textgraphx.adapters.rest_caller import _CircuitBreaker
    cb = _CircuitBreaker(threshold=3, cooldown=30)
    for _ in range(3):
        cb.record_failure("http://a")
    assert cb.is_open("http://a")
    assert not cb.is_open("http://b")


# ---------------------------------------------------------------------------
# callAllenNlpApi tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_callAllenNlpApi__cache_hit_bypasses_requests(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    rc._srl_cache.set("http://srl:8010/predict", "test sentence", {"verbs": [{"tags": ["B-V"]}]})
    post_mock = mock.MagicMock()
    monkeypatch.setattr(rc.requests, "post", post_mock)
    result = rc.callAllenNlpApi("semantic-role-labeling", "test sentence")
    post_mock.assert_not_called()
    assert result == {"verbs": [{"tags": ["B-V"]}]}


@pytest.mark.unit
def test_callAllenNlpApi__circuit_open_returns_empty(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    # Force circuit open
    url = "http://srl:8010/predict"
    for _ in range(rc._CB_FAILURE_THRESHOLD):
        rc._circuit_breaker.record_failure(url)
    post_mock = mock.MagicMock()
    monkeypatch.setattr(rc.requests, "post", post_mock)
    result = rc.callAllenNlpApi("semantic-role-labeling", "new sentence xyz")
    post_mock.assert_not_called()
    assert result == {}
    # Clean up
    rc._circuit_breaker.record_success(url)


@pytest.mark.unit
def test_callAllenNlpApi__successful_response_populates_cache(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    url = "http://srl:8010/predict"
    sentence = "unique sentence for cache test alpha"
    # Ensure not cached
    rc._srl_cache._store.pop(rc._srl_cache._key(url, sentence), None)
    resp_data = {"verbs": [{"frame": "run.01", "tags": ["B-V"]}]}
    mock_resp = mock.MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.text = '{"verbs": [{"frame": "run.01", "tags": ["B-V"]}]}'
    monkeypatch.setattr(rc.requests, "post", lambda *a, **kw: mock_resp)
    result = rc.callAllenNlpApi("semantic-role-labeling", sentence)
    assert result == resp_data
    assert rc._srl_cache.get(url, sentence) == resp_data


@pytest.mark.unit
def test_callAllenNlpApi__failure_records_circuit_breaker(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    import requests as req_lib
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    url = "http://srl:8010/predict"
    sentence = "failing sentence beta"
    rc._srl_cache._store.pop(rc._srl_cache._key(url, sentence), None)
    initial_failures = rc._circuit_breaker._failures.get(url, 0)
    def raise_error(*a, **kw):
        raise req_lib.exceptions.ConnectionError("down")
    monkeypatch.setattr(rc.requests, "post", raise_error)
    result = rc.callAllenNlpApi("semantic-role-labeling", sentence)
    assert result == {}
    assert rc._circuit_breaker._failures.get(url, 0) > initial_failures


# ---------------------------------------------------------------------------
# callNominalSrlApi tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_callNominalSrlApi__empty_url_returns_empty(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config(nom_srl_url=""))
    assert rc.callNominalSrlApi("anything") == {}


@pytest.mark.unit
def test_callNominalSrlApi__cache_hit_bypasses_requests(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    url = "http://nom:8011/predict_nom"
    sentence = "cached nominal sentence"
    rc._srl_cache.set(url, sentence, {"frames": [{"predicate": "attack"}]})
    post_mock = mock.MagicMock()
    monkeypatch.setattr(rc.requests, "post", post_mock)
    result = rc.callNominalSrlApi(sentence)
    post_mock.assert_not_called()
    assert result == {"frames": [{"predicate": "attack"}]}


@pytest.mark.unit
def test_callNominalSrlApi__circuit_open_returns_empty(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    url = "http://nom:8011/predict_nom"
    sentence = "unique nominal circuit test sentence"
    rc._srl_cache._store.pop(rc._srl_cache._key(url, sentence), None)
    for _ in range(rc._CB_FAILURE_THRESHOLD):
        rc._circuit_breaker.record_failure(url)
    post_mock = mock.MagicMock()
    monkeypatch.setattr(rc.requests, "post", post_mock)
    result = rc.callNominalSrlApi(sentence)
    post_mock.assert_not_called()
    assert result == {}
    rc._circuit_breaker.record_success(url)


# ---------------------------------------------------------------------------
# callNominalSrlApiBatch tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_callNominalSrlApiBatch__no_url_returns_empty_list(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    monkeypatch.setattr(rc, "get_config", lambda: _make_config(nom_srl_url=""))
    result = rc.callNominalSrlApiBatch(["s1", "s2", "s3"])
    assert result == [{}, {}, {}]


@pytest.mark.unit
def test_callNominalSrlApiBatch__returns_list_same_length(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    url = "http://nom:8011/predict_nom"
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    sentences = ["sent a", "sent b", "sent c"]
    # Pre-fill cache so no network calls needed
    for s in sentences:
        rc._srl_cache.set(url, s, {"frames": []})
    result = rc.callNominalSrlApiBatch(sentences)
    assert len(result) == 3


@pytest.mark.unit
def test_callNominalSrlApiBatch__cache_satisfies_all__no_async(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    url = "http://nom:8011/predict_nom"
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    sentences = ["fullcache_nom_1", "fullcache_nom_2"]
    expected = [{"frames": [{"predicate": "fall"}]}, {"frames": [{"predicate": "rise"}]}]
    for s, e in zip(sentences, expected):
        rc._srl_cache.set(url, s, e)
    # asyncio.run should NOT be called — the sync short-circuit path handles it
    run_calls: list = []
    original_run = rc.asyncio.run
    monkeypatch.setattr(rc.asyncio, "run", lambda coro: run_calls.append(coro) or {})
    result = rc.callNominalSrlApiBatch(sentences)
    assert len(run_calls) == 0, "asyncio.run should not be called when all sentences are cached"
    assert result == expected


@pytest.mark.unit
def test_callNominalSrlApiBatch__circuit_open_returns_all_empty(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    url = "http://nom:8011/predict_nom"
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    sentences = ["open1", "open2"]
    for s in sentences:
        rc._srl_cache._store.pop(rc._srl_cache._key(url, s), None)
    for _ in range(rc._CB_FAILURE_THRESHOLD):
        rc._circuit_breaker.record_failure(url)
    result = rc.callNominalSrlApiBatch(sentences)
    assert result == [{}, {}]
    rc._circuit_breaker.record_success(url)


# ---------------------------------------------------------------------------
# callAllenNlpApiBatch tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_callAllenNlpApiBatch__returns_list_same_length(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    url = "http://srl:8010/predict"
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    sentences = ["a", "b", "c"]
    for s in sentences:
        rc._srl_cache.set(url, s, {"verbs": []})
    result = rc.callAllenNlpApiBatch(sentences)
    assert len(result) == 3


@pytest.mark.unit
def test_callAllenNlpApiBatch__circuit_open_short_circuits(monkeypatch):
    import textgraphx.adapters.rest_caller as rc
    url = "http://srl:8010/predict"
    monkeypatch.setattr(rc, "get_config", lambda: _make_config())
    sentences = ["circuit_open_x", "circuit_open_y"]
    for s in sentences:
        rc._srl_cache._store.pop(rc._srl_cache._key(url, s), None)
    for _ in range(rc._CB_FAILURE_THRESHOLD):
        rc._circuit_breaker.record_failure(url)
    run_calls: list = []
    monkeypatch.setattr(rc.asyncio, "run", lambda coro: run_calls.append(coro) or [])
    result = rc.callAllenNlpApiBatch(sentences)
    # With circuit open, asyncio.run should NOT be called (sync short-circuit)
    assert len(run_calls) == 0, "asyncio.run should not be called when circuit is open"
    assert result == [{}, {}]
    rc._circuit_breaker.record_success(url)


# ---------------------------------------------------------------------------
# graph_based_nlp wiring: uses callNominalSrlApiBatch
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_graph_based_nlp__nominal_srl_uses_batch_caller():
    """Verify graph_based_nlp imports and calls callNominalSrlApiBatch (not the single-sentence variant)."""
    import ast
    import pathlib
    src = pathlib.Path(__file__).parent.parent.joinpath(
        "pipeline/ingestion/graph_based_nlp.py"
    ).read_text()
    assert "callNominalSrlApiBatch" in src, "graph_based_nlp should use callNominalSrlApiBatch"
    assert "callNominalSrlApi(" not in src or src.count("callNominalSrlApi(") == 0, \
        "graph_based_nlp should not use the single-sentence callNominalSrlApi"


@pytest.mark.unit
def test_graph_based_nlp__nominal_srl_no_per_sentence_loop():
    """Confirm the per-sentence loop over callNominalSrlApi is gone."""
    import pathlib
    src = pathlib.Path(__file__).parent.parent.joinpath(
        "pipeline/ingestion/graph_based_nlp.py"
    ).read_text()
    # Old pattern: 'for sent in doc.sents:' immediately followed by callNominalSrlApi
    assert "callNominalSrlApiBatch" in src
    # The single-sentence caller must not be called (check for open-paren to avoid
    # matching the Batch variant which is a superset string)
    assert "callNominalSrlApi(" not in src, \
        "graph_based_nlp must not call single-sentence callNominalSrlApi()"
