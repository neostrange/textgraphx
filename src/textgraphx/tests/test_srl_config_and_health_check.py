"""Unit tests for SRL service config defaults and legacy-schema warning.

Covers:
- srl_url defaults to port 8010 (transformer-srl)
- nom_srl_url defaults to port 8011 (CogComp)
- _detect_legacy_srl_schema correctly identifies old AllenNLP responses
- callAllenNlpApi emits a WARNING when the legacy schema is returned
"""
from __future__ import annotations

import logging
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests: ServicesConfig defaults
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_srl_url_default_is_port_8010():
    from textgraphx.infrastructure.config import ServicesConfig
    cfg = ServicesConfig()
    assert ":8010" in cfg.srl_url, (
        f"Expected srl_url to point to port 8010, got: {cfg.srl_url}"
    )


@pytest.mark.unit
def test_nom_srl_url_default_is_port_8011():
    from textgraphx.infrastructure.config import ServicesConfig
    cfg = ServicesConfig()
    assert ":8011" in cfg.nom_srl_url, (
        f"Expected nom_srl_url to point to port 8011, got: {cfg.nom_srl_url}"
    )


@pytest.mark.unit
def test_nom_srl_url_can_be_disabled_by_empty_string():
    from textgraphx.infrastructure.config import ServicesConfig
    cfg = ServicesConfig(nom_srl_url="")
    assert cfg.nom_srl_url == ""


# ---------------------------------------------------------------------------
# Tests: legacy schema detection
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_detect_legacy_schema__true_for_allennlp_response():
    from textgraphx.adapters.rest_caller import _detect_legacy_srl_schema
    legacy = {
        "verbs": [
            {"verb": "acquired", "description": "...", "tags": ["B-V", "B-ARG1"]},
        ]
    }
    assert _detect_legacy_srl_schema(legacy) is True


@pytest.mark.unit
def test_detect_legacy_schema__false_for_transformer_srl_response():
    from textgraphx.adapters.rest_caller import _detect_legacy_srl_schema
    modern = {
        "verbs": [
            {"verb": "acquired", "frame": "acquire.01", "frame_score": 0.93,
             "tags": ["B-V", "B-ARG1"]},
        ]
    }
    assert _detect_legacy_srl_schema(modern) is False


@pytest.mark.unit
def test_detect_legacy_schema__false_for_empty_verbs():
    from textgraphx.adapters.rest_caller import _detect_legacy_srl_schema
    assert _detect_legacy_srl_schema({"verbs": []}) is False


@pytest.mark.unit
def test_detect_legacy_schema__false_for_missing_verbs_key():
    from textgraphx.adapters.rest_caller import _detect_legacy_srl_schema
    assert _detect_legacy_srl_schema({}) is False


# ---------------------------------------------------------------------------
# Tests: callAllenNlpApi warning on legacy schema
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_callAllenNlpApi__warns_on_legacy_schema(caplog):
    import json
    from unittest.mock import patch, MagicMock

    legacy_body = json.dumps({
        "verbs": [
            {"verb": "run", "description": "...", "tags": ["B-V", "O"]},
        ]
    })

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = legacy_body

    with patch("textgraphx.adapters.rest_caller.requests.post", return_value=mock_response):
        with patch(
            "textgraphx.adapters.rest_caller.get_config"
        ) as mock_cfg:
            mock_cfg.return_value.services.srl_url = "http://localhost:8000/predict"
            mock_cfg.return_value.services.service_timeout_sec = 20
            with caplog.at_level(logging.WARNING, logger="textgraphx.adapters.rest_caller"):
                from textgraphx.adapters.rest_caller import callAllenNlpApi
                callAllenNlpApi("semantic-role-labeling", "He ran.")

    assert any(
        "legacy AllenNLP schema" in r.message or "legacy" in r.message.lower()
        for r in caplog.records
        if r.levelno >= logging.WARNING
    ), "Expected a WARNING about legacy schema"


@pytest.mark.unit
def test_callAllenNlpApi__no_warning_for_transformer_srl(caplog):
    import json
    from unittest.mock import patch, MagicMock

    modern_body = json.dumps({
        "verbs": [
            {"verb": "run", "frame": "run.01", "frame_score": 0.91, "tags": ["B-V", "O"]},
        ]
    })

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = modern_body

    with patch("textgraphx.adapters.rest_caller.requests.post", return_value=mock_response):
        with patch(
            "textgraphx.adapters.rest_caller.get_config"
        ) as mock_cfg:
            mock_cfg.return_value.services.srl_url = "http://localhost:8010/predict"
            mock_cfg.return_value.services.service_timeout_sec = 20
            with caplog.at_level(logging.WARNING, logger="textgraphx.adapters.rest_caller"):
                from textgraphx.adapters.rest_caller import callAllenNlpApi
                callAllenNlpApi("semantic-role-labeling", "He ran.")

    legacy_warns = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING and "legacy" in r.message.lower()
    ]
    assert not legacy_warns, f"Unexpected legacy schema warning: {legacy_warns}"
