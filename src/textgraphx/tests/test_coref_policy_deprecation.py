"""
Tests for coref backend policy enforcement.

Verifies that:
- Setting MAVERICK_COREF_URL triggers a DeprecationWarning at config load.
- Setting TEXTGRAPHX_MAVERICK_COREF_URL also triggers a DeprecationWarning.
- Not setting either env-var produces no DeprecationWarning for coref.
"""
import os
import warnings
import pytest


@pytest.mark.unit
class TestMaverickCorefDeprecation:
    """Phase-A contract: maverick-coref env-vars emit DeprecationWarning."""

    def _reload_config(self):
        """Import or reload the config loader so env-vars take effect."""
        import importlib
        import textgraphx.infrastructure.config as cfg_module
        importlib.reload(cfg_module)
        return cfg_module.get_config()

    def test_maverick_coref_url_warns(self, monkeypatch):
        monkeypatch.setenv("MAVERICK_COREF_URL", "http://localhost:9000")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self._reload_config()
        deprecation_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "maverick" in str(w.message).lower()
        ]
        assert deprecation_warnings, (
            "Expected a DeprecationWarning about maverick-coref when "
            "MAVERICK_COREF_URL is set"
        )

    def test_textgraphx_maverick_coref_url_warns(self, monkeypatch):
        monkeypatch.setenv("TEXTGRAPHX_MAVERICK_COREF_URL", "http://localhost:9000")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self._reload_config()
        deprecation_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "maverick" in str(w.message).lower()
        ]
        assert deprecation_warnings, (
            "Expected a DeprecationWarning about maverick-coref when "
            "TEXTGRAPHX_MAVERICK_COREF_URL is set"
        )

    def test_no_maverick_env_no_deprecation_warning(self, monkeypatch):
        monkeypatch.delenv("MAVERICK_COREF_URL", raising=False)
        monkeypatch.delenv("TEXTGRAPHX_MAVERICK_COREF_URL", raising=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self._reload_config()
        maverick_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "maverick" in str(w.message).lower()
        ]
        assert not maverick_warnings, (
            "Should not emit a maverick DeprecationWarning when no maverick env-var is set"
        )


@pytest.mark.unit
@pytest.mark.contract
class TestMaverickCorefDeprecationContract:
    """Contract: warning message must reference COREF_POLICY.md."""

    def _reload_config(self):
        import importlib
        import textgraphx.infrastructure.config as cfg_module
        importlib.reload(cfg_module)
        return cfg_module.get_config()

    def test_deprecation_message_references_policy_doc(self, monkeypatch):
        monkeypatch.setenv("MAVERICK_COREF_URL", "http://localhost:9000")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self._reload_config()
        deprecation_warnings = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "maverick" in str(w.message).lower()
        ]
        assert deprecation_warnings
        msg = str(deprecation_warnings[0].message)
        assert "COREF_POLICY.md" in msg, (
            f"DeprecationWarning should reference docs/COREF_POLICY.md; got: {msg!r}"
        )
