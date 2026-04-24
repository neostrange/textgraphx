"""Service-config contract tests (backlog item 1).

Validates that all external-service callers in the codebase read their URLs
and timeout parameters exclusively through ``get_config()`` / ``ServicesConfig``
rather than hard-coding host/port strings in production call paths.

No live services are needed; tests inspect source code and exercise the
config dataclass directly.

Coverage:
  - ServicesConfig has all required URL fields
  - RestCaller reads SRL URL from config
  - RestCaller reads HeidelTime URL from config
  - CallAllenNlpCoref reads coref URL from config
  - TextProcessor reads WSD URL from config
  - Service timeout read from config (no hard-coded integer literals in callers)
  - config.py default values are consistent with config.example.toml
  - Environment-variable overrides work for service URLs
  - INI config loading propagates service URLs
"""

import ast
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ----- Path constants --------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = REPO_ROOT / "textgraphx"
RESTCALLER_SRC = PKG_ROOT / "util" / "RestCaller.py"
COREF_SRC = PKG_ROOT / "util" / "CallAllenNlpCoref.py"
TEXT_PROC_SRC = PKG_ROOT / "TextProcessor.py"
CONFIG_SRC = PKG_ROOT / "config.py"
EXAMPLE_TOML = PKG_ROOT / "config.example.toml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ServicesConfig field contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestServicesConfigFields:
    """ServicesConfig dataclass must declare all required service URL fields."""

    required_fields = [
        "wsd_url",
        "coref_url",
        "temporal_url",
        "heideltime_url",
        "srl_url",
        "llm_url",
        "service_timeout_sec",
    ]

    def test_all_required_fields_declared(self):
        src = _read(CONFIG_SRC)
        for field in self.required_fields:
            assert field in src, f"ServicesConfig missing field: {field}"

    def test_services_config_is_dataclass(self):
        src = _read(CONFIG_SRC)
        assert "@dataclass" in src
        assert "class ServicesConfig" in src

    def test_wsd_url_has_default_value(self):
        src = _read(CONFIG_SRC)
        assert re.search(r'wsd_url\s*:\s*str\s*=', src)

    def test_coref_url_has_default_value(self):
        src = _read(CONFIG_SRC)
        assert re.search(r'coref_url\s*:\s*str\s*=', src)

    def test_srl_url_has_default_value(self):
        src = _read(CONFIG_SRC)
        assert re.search(r'srl_url\s*:\s*str\s*=', src)

    def test_heideltime_url_has_default_value(self):
        src = _read(CONFIG_SRC)
        assert re.search(r'heideltime_url\s*:\s*str\s*=', src)

    def test_service_timeout_has_default_value(self):
        src = _read(CONFIG_SRC)
        assert re.search(r'service_timeout_sec\s*:\s*int\s*=', src)


# ---------------------------------------------------------------------------
# Default-value consistency: config.py vs config.example.toml
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaultValueConsistency:
    """Defaults in config.py must align with the documented example config."""

    def test_heideltime_default_matches_example_toml(self):
        """Bug fix: heideltime_url was :5050 in config.py but :5000 in example."""
        py_src = _read(CONFIG_SRC)
        toml_src = _read(EXAMPLE_TOML)

        # Extract the default from config.py
        m = re.search(r'heideltime_url\s*:\s*str\s*=\s*"([^"]+)"', py_src)
        assert m, "Could not find heideltime_url default in config.py"
        py_default = m.group(1)

        # Extract from example toml
        m2 = re.search(r'heideltime_url\s*=\s*"([^"]+)"', toml_src)
        assert m2, "heideltime_url not found in config.example.toml"
        toml_default = m2.group(1)

        assert py_default == toml_default, (
            f"heideltime_url default mismatch: config.py={py_default!r} "
            f"vs config.example.toml={toml_default!r}"
        )

    def test_wsd_url_default_matches_example_toml(self):
        py_src = _read(CONFIG_SRC)
        toml_src = _read(EXAMPLE_TOML)
        m = re.search(r'wsd_url\s*:\s*str\s*=\s*"([^"]+)"', py_src)
        m2 = re.search(r'wsd_url\s*=\s*"([^"]+)"', toml_src)
        if m and m2:
            assert m.group(1) == m2.group(1), (
                f"wsd_url default mismatch: config.py={m.group(1)!r} vs toml={m2.group(1)!r}"
            )

    def test_coref_url_default_matches_example_toml(self):
        py_src = _read(CONFIG_SRC)
        toml_src = _read(EXAMPLE_TOML)
        m = re.search(r'coref_url\s*:\s*str\s*=\s*"([^"]+)"', py_src)
        m2 = re.search(r'coref_url\s*=\s*"([^"]+)"', toml_src)
        if m and m2:
            assert m.group(1) == m2.group(1), (
                f"coref_url default mismatch: config.py={m.group(1)!r} vs toml={m2.group(1)!r}"
            )

    def test_srl_url_default_matches_example_toml(self):
        py_src = _read(CONFIG_SRC)
        toml_src = _read(EXAMPLE_TOML)
        m = re.search(r'srl_url\s*:\s*str\s*=\s*"([^"]+)"', py_src)
        m2 = re.search(r'srl_url\s*=\s*"([^"]+)"', toml_src)
        if m and m2:
            assert m.group(1) == m2.group(1), (
                f"srl_url default mismatch: config.py={m.group(1)!r} vs toml={m2.group(1)!r}"
            )


# ---------------------------------------------------------------------------
# RestCaller source contract: no production hardcoded URLs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRestCallerSourceContract:
    def test_imports_get_config(self):
        src = _read(RESTCALLER_SRC)
        assert "from textgraphx.config import get_config" in src

    def test_srl_url_reads_from_config(self):
        """callAllenNlpApi must read srl_url via get_config()."""
        src = _read(RESTCALLER_SRC)
        assert "get_config().services.srl_url" in src

    def test_heideltime_url_reads_from_config(self):
        """callHeidelTimeService must read heideltime_url via get_config()."""
        src = _read(RESTCALLER_SRC)
        assert "get_config().services.heideltime_url" in src

    def test_timeout_reads_from_config(self):
        """_service_timeout must read from get_config().services.service_timeout_sec."""
        src = _read(RESTCALLER_SRC)
        assert "get_config().services.service_timeout_sec" in src

    def test_no_live_hardcoded_srl_port(self):
        """No active (non-comment) line should hardcode the SRL port :8000."""
        src = _read(RESTCALLER_SRC)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert ":8000" not in stripped, (
                f"Hardcoded :8000 in production code: {line!r}"
            )

    def test_no_live_hardcoded_heideltime_port(self):
        """No active line should hardcode the HeidelTime ports :5000 or :5050."""
        src = _read(RESTCALLER_SRC)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert ":5000" not in stripped and ":5050" not in stripped, (
                f"Hardcoded HeidelTime port in production code: {line!r}"
            )

    def test_amuse_wsd_callers_accept_endpoint_param(self):
        """amuse_wsd_api_call* must accept api_endpoint as a parameter (caller injects URL)."""
        src = _read(RESTCALLER_SRC)
        assert re.search(r"def amuse_wsd_api_call\w*\s*\([^)]*api_endpoint", src)


# ---------------------------------------------------------------------------
# CallAllenNlpCoref source contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorefCallerSourceContract:
    def test_imports_get_config(self):
        src = _read(COREF_SRC)
        assert "from textgraphx.config import get_config" in src

    def test_coref_url_reads_from_config(self):
        """callAllenNlpCoref must read coref_url via get_config()."""
        src = _read(COREF_SRC)
        assert "get_config().services.coref_url" in src

    def test_timeout_reads_from_config(self):
        """Coref caller must use timeout from config, not a hard-coded literal."""
        src = _read(COREF_SRC)
        assert "get_config().services.service_timeout_sec" in src

    def test_no_live_hardcoded_coref_port(self):
        """No active line should hardcode the coref port :9999."""
        src = _read(COREF_SRC)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert ":9999" not in stripped, (
                f"Hardcoded :9999 in active production code: {line!r}"
            )


# ---------------------------------------------------------------------------
# TextProcessor source contract: WSD URL injection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTextProcessorSourceContract:
    def test_imports_get_config(self):
        src = _read(TEXT_PROC_SRC)
        assert "from textgraphx.config import get_config" in src

    def test_wsd_url_reads_from_config(self):
        """TextProcessor must read wsd_url from cfg.services.wsd_url."""
        src = _read(TEXT_PROC_SRC)
        assert "cfg.services.wsd_url" in src or "get_config().services.wsd_url" in src

    def test_no_live_hardcoded_wsd_port(self):
        """No active line should hardcode the AMuSE-WSD port :81."""
        src = _read(TEXT_PROC_SRC)
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert ":81/" not in stripped, (
                f"Hardcoded :81 WSD port in active production code: {line!r}"
            )


# ---------------------------------------------------------------------------
# Runtime: ServicesConfig responds to env-var overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnvVarOverrides:
    """Config must respect TEXTGRAPHX_* env var overrides for service URLs."""

    def test_srl_url_env_override(self):
        env = {"TEXTGRAPHX_SRL_URL": "http://myhost:1234/predict"}
        with patch.dict(os.environ, env, clear=False):
            # Force re-load
            import importlib
            import textgraphx.config as cfg_mod
            importlib.reload(cfg_mod)
            cfg = cfg_mod.get_config()
            assert cfg.services.srl_url == "http://myhost:1234/predict"

    def test_coref_url_env_override(self):
        env = {"TEXTGRAPHX_COREF_URL": "http://coref-prod:9999/coreference_resolution"}
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import textgraphx.config as cfg_mod
            importlib.reload(cfg_mod)
            cfg = cfg_mod.get_config()
            assert cfg.services.coref_url == "http://coref-prod:9999/coreference_resolution"

    def test_heideltime_url_env_override(self):
        env = {"TEXTGRAPHX_HEIDELTIME_URL": "http://heideltime-prod:5000/annotate"}
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import textgraphx.config as cfg_mod
            importlib.reload(cfg_mod)
            cfg = cfg_mod.get_config()
            assert cfg.services.heideltime_url == "http://heideltime-prod:5000/annotate"

    def test_wsd_url_env_override(self):
        env = {"TEXTGRAPHX_WSD_URL": "http://wsd-prod:81/api/model"}
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import textgraphx.config as cfg_mod
            importlib.reload(cfg_mod)
            cfg = cfg_mod.get_config()
            assert cfg.services.wsd_url == "http://wsd-prod:81/api/model"


# ---------------------------------------------------------------------------
# INI config loading propagates service URLs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIniConfigLoading:
    """config.py must read service URLs from [services] section of an INI file."""

    def test_ini_loading_reads_services_section(self, tmp_path):
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(
            "[services]\n"
            "srl_url = http://ini-host:8888/predict\n"
            "coref_url = http://ini-coref:9999/coreference_resolution\n",
            encoding="utf-8",
        )
        import importlib
        import textgraphx.config as cfg_mod
        importlib.reload(cfg_mod)
        cfg = cfg_mod.load_config(str(ini_file))
        assert cfg.services.srl_url == "http://ini-host:8888/predict"
        assert cfg.services.coref_url == "http://ini-coref:9999/coreference_resolution"

    def test_ini_loading_missing_key_falls_back_to_default(self, tmp_path):
        ini_file = tmp_path / "minimal.ini"
        ini_file.write_text(
            "[services]\n"
            "srl_url = http://override:8080/predict\n",
            encoding="utf-8",
        )
        import importlib
        import textgraphx.config as cfg_mod
        importlib.reload(cfg_mod)
        cfg = cfg_mod.load_config(str(ini_file))
        # coref_url was not in the INI, so must fall back to dataclass default
        assert "localhost" in cfg.services.coref_url


# ---------------------------------------------------------------------------
# config.py source contract: env-var reading for all service keys
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigSourceEnvVarCoverage:
    """config.py must contain env-var override logic for all primary service URLs."""

    required_env_keys = [
        "TEXTGRAPHX_SRL_URL",
        "TEXTGRAPHX_COREF_URL",
        "TEXTGRAPHX_WSD_URL",
        "TEXTGRAPHX_HEIDELTIME_URL",
        "TEXTGRAPHX_LLM_URL",
        "TEXTGRAPHX_TEMPORAL_URL",
    ]

    def test_all_env_keys_referenced_in_config_source(self):
        src = _read(CONFIG_SRC)
        for key in self.required_env_keys:
            assert key in src, (
                f"config.py does not reference env var {key!r} — "
                "service URL override will not work"
            )
