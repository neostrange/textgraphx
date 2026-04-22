"""Phase-0 tests for local service caller robustness and timeout configuration."""

import json
from types import SimpleNamespace

import pytest


class _FakeResponse:
    def __init__(self, text='{}', status_ok=True):
        self.text = text
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("http error")

    def json(self):
        return json.loads(self.text)


@pytest.mark.unit
def test_call_allennlp_api_uses_configured_timeout(monkeypatch):
    from textgraphx.util import RestCaller

    fake_cfg = SimpleNamespace(services=SimpleNamespace(service_timeout_sec=9, srl_url="http://localhost:8000/predict"))
    seen = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        seen["url"] = url
        seen["timeout"] = timeout
        return _FakeResponse(text='{"ok": true}')

    monkeypatch.setattr(RestCaller, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(RestCaller.requests, "post", fake_post)

    payload = RestCaller.callAllenNlpApi("semantic-role-labeling", "Stocks fell")
    assert payload["ok"] is True
    assert seen["url"] == "http://localhost:8000/predict"
    assert seen["timeout"] == 9


@pytest.mark.unit
def test_call_allennlp_api_returns_empty_dict_on_invalid_json(monkeypatch):
    from textgraphx.util import RestCaller

    fake_cfg = SimpleNamespace(services=SimpleNamespace(service_timeout_sec=3, srl_url="http://localhost:8000/predict"))

    def fake_post(url, headers=None, data=None, timeout=None):
        return _FakeResponse(text='not json')

    monkeypatch.setattr(RestCaller, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(RestCaller.requests, "post", fake_post)

    payload = RestCaller.callAllenNlpApi("semantic-role-labeling", "Stocks fell")
    assert payload == {}


@pytest.mark.unit
def test_call_allennlp_coref_uses_timeout_and_handles_failures(monkeypatch):
    from textgraphx.util import CallAllenNlpCoref

    fake_cfg = SimpleNamespace(services=SimpleNamespace(service_timeout_sec=11, coref_url="http://localhost:9999/coreference_resolution"))
    seen = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        seen["url"] = url
        seen["timeout"] = timeout
        return _FakeResponse(text='{"clusters": []}')

    monkeypatch.setattr(CallAllenNlpCoref, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(CallAllenNlpCoref.requests, "post", fake_post)

    payload = CallAllenNlpCoref.callAllenNlpCoref("coreference-resolution", "The bank said it will act.")
    assert payload["clusters"] == []
    assert seen["url"] == "http://localhost:9999/coreference_resolution"
    assert seen["timeout"] == 11
