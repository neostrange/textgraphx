"""Phase-0 tests for shared service timeout config wiring."""

import pytest


@pytest.mark.unit
def test_services_timeout_env_override(monkeypatch):
    import textgraphx.infrastructure.config as cfg

    monkeypatch.setenv("SERVICE_TIMEOUT_SEC", "17")
    cfg._CACHED = None
    loaded = cfg.load_config(path=None, allow_env=True)

    assert loaded.services.service_timeout_sec == 17


@pytest.mark.unit
def test_services_timeout_defaults_positive():
    import textgraphx.infrastructure.config as cfg

    cfg._CACHED = None
    loaded = cfg.load_config(path=None, allow_env=False)

    assert loaded.services.service_timeout_sec >= 1


@pytest.mark.unit
def test_runtime_tlink_shadow_mode_env_override(monkeypatch):
    import textgraphx.infrastructure.config as cfg

    monkeypatch.setenv("TEXTGRAPHX_TLINK_SHADOW_MODE", "true")
    cfg._CACHED = None
    loaded = cfg.load_config(path=None, allow_env=True)

    assert loaded.runtime.tlink_shadow_mode is True


@pytest.mark.unit
def test_runtime_cross_document_fusion_env_override(monkeypatch):
    import textgraphx.infrastructure.config as cfg

    monkeypatch.setenv("TEXTGRAPHX_ENABLE_CROSS_DOCUMENT_FUSION", "true")
    cfg._CACHED = None
    loaded = cfg.load_config(path=None, allow_env=True)

    assert loaded.runtime.enable_cross_document_fusion is True
