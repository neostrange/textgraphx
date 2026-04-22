"""Milestone 10: CI/CD Integration & Quality Automation.

Automates quality verification through:
  - Quality gate enforcement (configurable thresholds)
  - PR/review automation (comments, status checks)
  - Local pre-commit verification
  - Dashboard and trend tracking
  - Automated remediation recommendations

Provides:
  - QualityGateConfig: Configurable quality requirements
  - CIReportGenerator: GitHub Actions and CI-compatible output
  - LocalPrecommitChecker: Fast quality checks for developers
  - QualityTrendTracker: Track quality over time
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from textgraphx.evaluation.meantime_bridge import ConsolidatedQualityReport
from textgraphx.evaluation.cross_phase_validator import ConsistencyReport


@dataclass
class QualityGateConfig:
    """Configurable quality gate requirements."""

    min_overall_quality: float = 0.80  # Overall quality threshold
    min_phase_quality: float = 0.70    # Minimum quality per phase
    min_meantime_f1: float = 0.75      # MEANTIME gold-standard threshold
    min_consistency: float = 0.90      # Cross-phase consistency threshold
    require_no_errors: bool = True     # Fail if consistency errors exist
    require_deterministic: bool = True # Fail if non-deterministic
    produce_pr_comment: bool = True    # Generate PR comment on GitHub
    enable_trend_tracking: bool = True # Track quality over time

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "min_overall_quality": self.min_overall_quality,
            "min_phase_quality": self.min_phase_quality,
            "min_meantime_f1": self.min_meantime_f1,
            "min_consistency": self.min_consistency,
            "require_no_errors": self.require_no_errors,
            "require_deterministic": self.require_deterministic,
            "produce_pr_comment": self.produce_pr_comment,
            "enable_trend_tracking": self.enable_trend_tracking,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> QualityGateConfig:
        """Deserialize from dict."""
        return QualityGateConfig(**d)

    @staticmethod
    def strict() -> QualityGateConfig:
        """Strict mode (production)."""
        return QualityGateConfig(
            min_overall_quality=0.90,
            min_phase_quality=0.85,
            min_meantime_f1=0.85,
            min_consistency=0.95,
            require_no_errors=True,
            require_deterministic=True,
        )

    @staticmethod
    def relaxed() -> QualityGateConfig:
        """Relaxed mode (development)."""
        return QualityGateConfig(
            min_overall_quality=0.70,
            min_phase_quality=0.60,
            min_meantime_f1=0.65,
            min_consistency=0.80,
            require_no_errors=False,
            require_deterministic=False,
        )


@dataclass
class QualityGateResult:
    """Result of quality gate verification."""

    passed: bool
    overall_score: float
    config: QualityGateConfig
    violations: List[str] = field(default_factory=list)  # Failed checks
    warnings: List[str] = field(default_factory=list)    # Warnings
    recommendations: List[str] = field(default_factory=list)  # Suggested fixes
    gate_name: str = "evaluation_gate"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "passed": self.passed,
            "overall_score": self.overall_score,
            "status": "✅ PASS" if self.passed else "❌ FAIL",
            "violations": self.violations,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "gate_name": self.gate_name,
        }

    def to_exit_code(self) -> int:
        """Convert to shell exit code."""
        return 0 if self.passed else 1

    def to_github_actions_output(self) -> str:
        """Generate GitHub Actions compatible output."""
        lines = [
            f"::{'error' if not self.passed else 'notice'} title=Quality Gate {'PASSED ✅' if self.passed else 'FAILED ❌'}::",
            f"Overall Quality: {self.overall_score:.4f}",
        ]

        if self.violations:
            lines.append("Violations:")
            for v in self.violations:
                lines.append(f"  - {v}")

        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")

        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")

        return "\n".join(lines)

    def to_pr_comment(self) -> str:
        """Generate GitHub PR comment."""
        status_emoji = "✅" if self.passed else "❌"
        lines = [
            f"## {status_emoji} Quality Gate: {self.gate_name.upper()}",
            "",
            f"**Status**: {'PASSED' if self.passed else 'FAILED'}",
            f"**Overall Quality Score**: `{self.overall_score:.4f}`",
            "",
        ]

        if self.violations:
            lines.extend([
                "### 🔴 Violations",
                "",
            ])
            for v in self.violations:
                lines.append(f"- {v}")
            lines.append("")

        if self.warnings:
            lines.extend([
                "### ⚠️ Warnings",
                "",
            ])
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if self.recommendations:
            lines.extend([
                "### 💡 Recommendations",
                "",
            ])
            for r in self.recommendations:
                lines.append(f"- {r}")
            lines.append("")

        return "\n".join(lines)


class QualityGateVerifierCI:
    """Verifies quality gates for CI/CD integration."""

    def __init__(self, config: Optional[QualityGateConfig] = None):
        """Initialize verifier.

        Args:
            config: QualityGateConfig (default: standard)
        """
        self.config = config or QualityGateConfig()

    def verify(
        self,
        report: ConsolidatedQualityReport,
        consistency_report: Optional[ConsistencyReport] = None,
    ) -> QualityGateResult:
        """Run quality gate verification.

        Args:
            report: ConsolidatedQualityReport from M8a
            consistency_report: Optional ConsistencyReport from M8b

        Returns:
            QualityGateResult with pass/fail status
        """
        violations = []
        warnings = []
        recommendations = []
        overall_score = report.overall_quality()

        # Check overall quality
        if overall_score < self.config.min_overall_quality:
            violations.append(
                f"Overall quality {overall_score:.4f} below minimum {self.config.min_overall_quality:.4f}"
            )
            recommendations.append("Review phase-level quality scores and identify low-scoring phases")

        # Check phase-level quality
        phase_scores = report.evaluation_suite.quality_scores()
        low_phases = [p for p, s in phase_scores.items() if s < self.config.min_phase_quality]
        if low_phases:
            for phase in low_phases:
                violations.append(
                    f"Phase '{phase}' quality {phase_scores[phase]:.4f} below minimum {self.config.min_phase_quality:.4f}"
                )
            recommendations.append(f"Debug failing phases: {', '.join(low_phases)}")

        # Check MEANTIME quality
        meantime_score = report.meantime_quality_score()
        if meantime_score < self.config.min_meantime_f1:
            violations.append(
                f"MEANTIME F1 {meantime_score:.4f} below minimum {self.config.min_meantime_f1:.4f}"
            )
            recommendations.append("Review gold-standard validation results and span matching")

        # Check consistency
        consistency_score = report.consistency_score()
        if consistency_score < self.config.min_consistency:
            violations.append(
                f"Cross-layer consistency {consistency_score:.4f} below minimum {self.config.min_consistency:.4f}"
            )

        # Check for consistency errors
        if consistency_report and self.config.require_no_errors:
            if consistency_report.error_count() > 0:
                violations.append(f"Consistency errors detected: {consistency_report.error_count()}")
                recommendations.append("Review cross-phase invariant violations")

        # Check determinism
        run_metadata = report.run_metadata
        if self.config.require_deterministic and not run_metadata.seed:
            warnings.append("Determinism not verified (no seed captured)")

        # Determine overall pass/fail
        passed = len(violations) == 0

        return QualityGateResult(
            passed=passed,
            overall_score=overall_score,
            config=self.config,
            violations=violations,
            warnings=warnings,
            recommendations=recommendations,
        )


class CIReportGenerator:
    """Generates CI-compatible quality reports."""

    @staticmethod
    def github_actions_output(gate_result: QualityGateResult) -> str:
        """Generate GitHub Actions output format."""
        return gate_result.to_github_actions_output()

    @staticmethod
    def pr_comment(gate_result: QualityGateResult) -> str:
        """Generate PR comment format."""
        return gate_result.to_pr_comment()

    @staticmethod
    def json_report(
        gate_result: QualityGateResult,
        output_path: Optional[Path] = None,
    ) -> str | Path:
        """Generate JSON report.

        Args:
            gate_result: QualityGateResult to report
            output_path: Optional path to write report

        Returns:
            JSON string if no output_path, else Path to written file
        """
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gate_result": gate_result.to_dict(),
        }
        json_str = json.dumps(data, indent=2)

        if output_path:
            Path(output_path).write_text(json_str)
            return Path(output_path)

        return json_str

    @staticmethod
    def markdown_report(
        gate_result: QualityGateResult,
        output_path: Optional[Path] = None,
    ) -> str | Path:
        """Generate markdown report.

        Args:
            gate_result: QualityGateResult to report
            output_path: Optional path to write report

        Returns:
            Markdown string if no output_path, else Path to written file
        """
        markdown = gate_result.to_pr_comment()

        if output_path:
            Path(output_path).write_text(markdown)
            return Path(output_path)

        return markdown


@dataclass
class QualityTrendPoint:
    """Single point in quality trend."""

    timestamp: str
    quality_score: float
    version: str = ""
    commit_sha: str = ""
    branch: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
            "version": self.version,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
        }


class QualityTrendTracker:
    """Tracks and visualizes quality trends over time."""

    def __init__(self, trend_file: Path | str = Path("trend.json")):
        """Initialize tracker.

        Args:
            trend_file: Path to trend history file
        """
        self.trend_file = Path(trend_file)
        self.points: List[QualityTrendPoint] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        """Load trend history from file."""
        if self.trend_file.exists():
            with self.trend_file.open("r") as f:
                data = json.load(f)
            self.points = [QualityTrendPoint(**p) for p in data.get("points", [])]

    def record(
        self,
        report: ConsolidatedQualityReport,
        version: str = "",
        commit_sha: str = "",
        branch: str = "",
    ) -> None:
        """Record a quality point.

        Args:
            report: ConsolidatedQualityReport to record
            version: Optional version tag
            commit_sha: Optional commit SHA
            branch: Optional branch name
        """
        point = QualityTrendPoint(
            timestamp=str(report.run_metadata.timestamp),
            quality_score=report.overall_quality(),
            version=version,
            commit_sha=commit_sha,
            branch=branch,
        )
        self.points.append(point)
        self._save_to_file()

    def _save_to_file(self) -> None:
        """Persist trend to file."""
        data = {
            "points": [p.to_dict() for p in self.points],
        }
        self.trend_file.parent.mkdir(parents=True, exist_ok=True)
        with self.trend_file.open("w") as f:
            json.dump(data, f, indent=2)

    def trend_summary(self) -> Dict[str, Any]:
        """Get trend summary statistics."""
        if not self.points:
            return {"point_count": 0}

        scores = [p.quality_score for p in self.points]
        return {
            "point_count": len(self.points),
            "earliest_timestamp": self.points[0].timestamp,
            "latest_timestamp": self.points[-1].timestamp,
            "earliest_score": self.points[0].quality_score,
            "latest_score": self.points[-1].quality_score,
            "min_score": min(scores),
            "max_score": max(scores),
            "trend_direction": "📈 improving" if self.points[-1].quality_score > self.points[0].quality_score else "📉 declining",
        }

    def to_markdown(self) -> str:
        """Generate markdown trend report."""
        summary = self.trend_summary()
        lines = [
            "## 📊 Quality Trend",
            "",
            f"**Data Points**: {summary.get('point_count', 0)}",
            f"**Trend**: {summary.get('trend_direction', 'unknown')}",
            f"**Range**: `[{summary.get('min_score', 0):.4f}, {summary.get('max_score', 0):.4f}]`",
            "",
        ]

        if self.points:
            lines.extend([
                "### Recent History",
                "",
                "| Timestamp | Quality | Version | Branch |",
                "|-----------|---------|---------|--------|",
            ])
            for point in self.points[-10:]:  # Show last 10
                lines.append(
                    f"| {point.timestamp[:10]} | `{point.quality_score:.4f}` | {point.version or '-'} | {point.branch or '-'} |"
                )

        return "\n".join(lines)


class LocalPrecommitChecker:
    """Fast quality checks for local pre-commit hook."""

    def __init__(self, config: Optional[QualityGateConfig] = None):
        """Initialize checker.

        Args:
            config: QualityGateConfig (default: relaxed for local checks)
        """
        self.config = config or QualityGateConfig.relaxed()

    def quick_check(self, report: ConsolidatedQualityReport) -> Tuple[bool, str]:
        """Perform quick sanity check on report.

        Args:
            report: ConsolidatedQualityReport to check

        Returns:
            Tuple of (passed, message)
        """
        overall = report.overall_quality()

        if overall < self.config.min_overall_quality:
            return (
                False,
                f"Quality {overall:.4f} below minimum {self.config.min_overall_quality:.4f}",
            )

        phase_scores = report.evaluation_suite.quality_scores()
        if any(s < self.config.min_phase_quality for s in phase_scores.values()):
            return (
                False,
                f"One or more phases below minimum {self.config.min_phase_quality:.4f}",
            )

        return True, f"✅ Quality check passed ({overall:.4f})"
