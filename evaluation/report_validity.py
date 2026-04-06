"""Report validity metadata and schema standardization for evaluation artifacts.

This module provides unified validity headers and metadata tracking for all
evaluation reports, ensuring that comparisons include full parameter documentation
and can be validated for reproducibility and confounding factors.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class RunMetadata:
    """Complete run parameter fingerprint for reproducibility and comparison validity."""

    dataset_hash: str  # SHA256 of dataset file list or config
    config_hash: str   # SHA256 of deployment/runtime config
    seed: int          # Random seed or determinism indicator
    strict_gate_enabled: bool  # Whether strict transition gate was active
    fusion_enabled: bool       # Whether cross-document fusion was enabled
    cleanup_mode: str          # "full" | "auto" | "none"
    timestamp: str             # ISO 8601 UTC timestamp of run start
    duration_seconds: Optional[float] = None  # Elapsed time of evaluation

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON embedding."""
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> RunMetadata:
        """Deserialize from dict."""
        return RunMetadata(**d)


@dataclass
class ValidityHeader:
    """Header section for evaluation artifacts certifying comparability and reproducibility."""

    run_metadata: RunMetadata
    determinism_checked: bool = False
    determinism_pass: Optional[bool] = None  # None = not checked, True = passed, False = failed
    feature_activation_evidence: Dict[str, Any] = field(default_factory=dict)
    # Expected: {"same_as_edges": 42, "co_occurs_edges": 15, ...} or empty if not applicable

    inconclusive_reasons: list[str] = field(default_factory=list)
    # Populated if this run is inconclusive; e.g., ["fusion_enabled=true but SAME_AS=0"]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for YAML frontmatter or JSON embedding."""
        return {
            "run_metadata": self.run_metadata.to_dict(),
            "determinism_checked": self.determinism_checked,
            "determinism_pass": self.determinism_pass,
            "feature_activation_evidence": self.feature_activation_evidence,
            "inconclusive_reasons": self.inconclusive_reasons,
            "is_conclusive": len(self.inconclusive_reasons) == 0,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> ValidityHeader:
        """Deserialize from dict."""
        return ValidityHeader(
            run_metadata=RunMetadata.from_dict(d["run_metadata"]),
            determinism_checked=d.get("determinism_checked", False),
            determinism_pass=d.get("determinism_pass"),
            feature_activation_evidence=d.get("feature_activation_evidence", {}),
            inconclusive_reasons=d.get("inconclusive_reasons", []),
        )


def render_validity_header_yaml(header: ValidityHeader) -> str:
    """Render ValidityHeader as YAML frontmatter for markdown reports.

    Example output::

        ---
        run_metadata:
          dataset_hash: "abc...def"
          config_hash: "xyz...123"
          seed: 42
          strict_gate_enabled: true
          fusion_enabled: false
          cleanup_mode: "auto"
          timestamp: "2026-04-05T12:34:56Z"
          duration_seconds: 123.45
        determinism_checked: true
        determinism_pass: true
        feature_activation_evidence: {}
        inconclusive_reasons: []
        is_conclusive: true
        ---
    """
    d = header.to_dict()
    lines = ["---"]
    lines.extend(_dict_to_yaml_lines(d, indent=0))
    lines.append("---")
    return "\n".join(lines)


def render_validity_header_json(header: ValidityHeader) -> Dict[str, Any]:
    """Render ValidityHeader for JSON embedding at report root."""
    return {
        "validity_header": header.to_dict(),
    }


def _dict_to_yaml_lines(d: Dict[str, Any], indent: int = 0) -> list[str]:
    """Convert dict to YAML-like string lines (simplistic, for readability)."""
    lines = []
    indent_str = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{indent_str}{k}:")
            lines.extend(_dict_to_yaml_lines(v, indent + 1))
        elif isinstance(v, list):
            if not v:
                lines.append(f"{indent_str}{k}: []")
            else:
                lines.append(f"{indent_str}{k}:")
                for item in v:
                    if isinstance(item, dict):
                        lines.append(f"{indent_str}  -")
                        lines.extend(_dict_to_yaml_lines(item, indent + 2))
                    else:
                        lines.append(f"{indent_str}  - {_quote_yaml_value(item)}")
        elif isinstance(v, bool):
            lines.append(f"{indent_str}{k}: {str(v).lower()}")
        elif v is None:
            lines.append(f"{indent_str}{k}: null")
        else:
            lines.append(f"{indent_str}{k}: {_quote_yaml_value(v)}")
    return lines


def _quote_yaml_value(v: Any) -> str:
    """Quote a YAML value if it contains special characters."""
    s = str(v)
    if any(c in s for c in ": \t\n"):
        return f'"{s}"'
    return s


def compute_dataset_hash(gold_file_paths: list[Path]) -> str:
    """Compute a stable hash of dataset file metadata (names and sizes).

    This avoids reading entire files and ensures deterministic hashing.
    """
    h = hashlib.sha256()
    for p in sorted(gold_file_paths):
        h.update(f"{p.name}:{p.stat().st_size}\n".encode())
    return h.hexdigest()[:16]


def compute_config_hash(config_dict: Dict[str, Any]) -> str:
    """Compute a stable hash of a config dict (sorted JSON)."""
    h = hashlib.sha256()
    h.update(json.dumps(config_dict, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def check_fusion_activation(
    fusion_enabled: bool,
    same_as_count: int,
    co_occurs_count: int,
) -> tuple[bool, list[str]]:
    """Evaluate whether fusion feature activated in a run result.

    Returns:
        (is_conclusive, inconclusive_reasons)
    """
    reasons = []
    if fusion_enabled and same_as_count == 0 and co_occurs_count == 0:
        reasons.append(f"fusion_enabled={fusion_enabled} but SAME_AS edges created={same_as_count}, CO_OCCURS edges created={co_occurs_count}")
    return len(reasons) == 0, reasons
