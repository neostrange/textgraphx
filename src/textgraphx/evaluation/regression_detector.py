"""Milestone 9: Regression Detection & Variance Analysis.

Ensures pipeline improvements are real (not random variation) through:
  - Baseline capture and persistence
  - Run-to-run comparison with tolerance thresholds
  - Statistical variance analysis across multiple runs
  - Determinism verification and reproducibility proof
  - Regression detection with diagnostic reporting

Provides:
  - BaselineManager: Capture and load baseline reports
  - RegressionDetector: Compare current vs baseline
  - VarianceAnalyzer: Compute variance across multiple runs
  - QualityGateVerifier: Statistical significance testing
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, stdev, variance

from textgraphx.evaluation.meantime_bridge import ConsolidatedQualityReport
from textgraphx.evaluation.fullstack_harness import EvaluationSuite


@dataclass
class BaselineMetrics:
    """Captured baseline metrics for comparison."""

    timestamp: str
    version: str  # Baseline version (e.g., "v1.0", "2025-04-05")
    quality_score: float
    phase_scores: Dict[str, float] = field(default_factory=dict)
    meantime_f1: float = 0.0
    consistency_score: float = 0.0
    config_hash: str = ""
    dataset_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "quality_score": self.quality_score,
            "phase_scores": self.phase_scores,
            "meantime_f1": self.meantime_f1,
            "consistency_score": self.consistency_score,
            "config_hash": self.config_hash,
            "dataset_hash": self.dataset_hash,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> BaselineMetrics:
        """Deserialize from dict."""
        return BaselineMetrics(**d)

    @staticmethod
    def from_report(report: ConsolidatedQualityReport, version: str = "v1.0") -> BaselineMetrics:
        """Create baseline from consolidated report."""
        return BaselineMetrics(
            timestamp=str(report.run_metadata.timestamp),
            version=version,
            quality_score=report.overall_quality(),
            phase_scores=report.evaluation_suite.quality_scores(),
            meantime_f1=report.meantime_quality_score(),
            consistency_score=report.consistency_score(),
            config_hash=report.run_metadata.config_hash,
            dataset_hash=report.run_metadata.dataset_hash,
        )


@dataclass
class RegressionAnalysis:
    """Results of regression detection."""

    baseline_version: str
    current_quality: float
    baseline_quality: float
    quality_delta: float  # Current - baseline (negative = regression)
    percent_change: float  # (current - baseline) / baseline * 100
    is_regression: bool
    phase_regressions: Dict[str, float] = field(default_factory=dict)  # phase -> delta
    significance_level: float = 0.05  # Statistical significance threshold
    confidence_level: float = 0.95
    diagnostic_notes: List[str] = field(default_factory=list)

    def severity(self) -> str:
        """Categorize regression severity."""
        if not self.is_regression:
            return "IMPROVEMENT"
        if abs(self.quality_delta) < 0.01:
            return "ACCEPTABLE"  # < 1% regression
        elif abs(self.quality_delta) < 0.05:
            return "WARNING"  # 1-5% regression
        else:
            return "CRITICAL"  # > 5% regression

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "baseline_version": self.baseline_version,
            "current_quality": self.current_quality,
            "baseline_quality": self.baseline_quality,
            "quality_delta": self.quality_delta,
            "percent_change": self.percent_change,
            "is_regression": self.is_regression,
            "severity": self.severity(),
            "phase_regressions": self.phase_regressions,
            "diagnostic_notes": self.diagnostic_notes,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        severity_emoji = {
            "IMPROVEMENT": "⬆️",
            "ACCEPTABLE": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🔴",
        }
        emoji = severity_emoji.get(self.severity(), "❓")

        lines = [
            f"## {emoji} Regression Analysis",
            "",
            f"**Baseline Version**: {self.baseline_version}",
            f"**Quality Change**: `{self.quality_delta:+.4f}` ({self.percent_change:+.1f}%)",
            f"**Severity**: {self.severity()}",
            "",
            "| Metric | Baseline | Current | Delta |",
            "|--------|----------|---------|-------|",
            f"| Overall Quality | `{self.baseline_quality:.4f}` | `{self.current_quality:.4f}` | `{self.quality_delta:+.4f}` |",
        ]

        if self.phase_regressions:
            lines.extend([
                "",
                "### Phase-Level Regressions",
                "",
            ])
            for phase, delta in sorted(self.phase_regressions.items(), key=lambda x: x[1]):
                status = "📉" if delta < 0 else "📈"
                lines.append(f"{status} **{phase}**: `{delta:+.4f}`")

        if self.diagnostic_notes:
            lines.extend([
                "",
                "### Diagnostic Notes",
                "",
            ])
            for note in self.diagnostic_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)


@dataclass
class VarianceReport:
    """Results of variance analysis across multiple runs."""

    run_count: int
    quality_scores: List[float] = field(default_factory=list)
    mean_quality: float = 0.0
    std_dev: float = 0.0
    variance: float = 0.0
    min_quality: float = 1.0
    max_quality: float = 0.0
    coefficient_of_variation: float = 0.0  # std_dev / mean
    is_deterministic: bool = False
    determinism_tolerance: float = 0.0001  # Maximum acceptable variance

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "run_count": self.run_count,
            "quality_scores": self.quality_scores,
            "mean_quality": self.mean_quality,
            "std_dev": self.std_dev,
            "variance": self.variance,
            "min_quality": self.min_quality,
            "max_quality": self.max_quality,
            "coefficient_of_variation": self.coefficient_of_variation,
            "is_deterministic": self.is_deterministic,
            "determinism_tolerance": self.determinism_tolerance,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        determinism_icon = "✅" if self.is_deterministic else "⚠️"
        lines = [
            f"## {determinism_icon} Variance Analysis",
            "",
            f"**Runs Analyzed**: {self.run_count}",
            f"**Deterministic**: {self.is_deterministic}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Mean Quality | `{self.mean_quality:.4f}` |",
            f"| Std Dev | `{self.std_dev:.6f}` |",
            f"| Variance | `{self.variance:.6f}` |",
            f"| Coeff of Variation | `{self.coefficient_of_variation:.4%}` |",
            f"| Range | `[{self.min_quality:.4f}, {self.max_quality:.4f}]` |",
        ]
        return "\n".join(lines)


class BaselineManager:
    """Manages baseline capture, persistence, and retrieval."""

    def __init__(self, baseline_dir: Path | str = Path("baselines")):
        """Initialize baseline manager.

        Args:
            baseline_dir: Directory to store baseline files
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(
        self,
        report: ConsolidatedQualityReport,
        version: str = "v1.0",
    ) -> Path:
        """Capture and save baseline from consolidated report.

        Args:
            report: ConsolidatedQualityReport to capture
            version: Baseline version identifier

        Returns:
            Path to saved baseline file
        """
        baseline = BaselineMetrics.from_report(report, version=version)
        filename = f"baseline_{version.replace('.', '_')}.json"
        filepath = self.baseline_dir / filename

        with filepath.open("w") as f:
            json.dump(baseline.to_dict(), f, indent=2)

        return filepath

    def load_baseline(self, version: str = "v1.0") -> Optional[BaselineMetrics]:
        """Load baseline metrics.

        Args:
            version: Baseline version to load

        Returns:
            BaselineMetrics if found, None otherwise
        """
        filename = f"baseline_{version.replace('.', '_')}.json"
        filepath = self.baseline_dir / filename

        if not filepath.exists():
            return None

        with filepath.open("r") as f:
            data = json.load(f)

        return BaselineMetrics.from_dict(data)

    def list_baselines(self) -> List[str]:
        """List all available baselines."""
        baselines = []
        for filepath in sorted(self.baseline_dir.glob("baseline_*.json")):
            version = filepath.stem.replace("baseline_", "").replace("_", ".")
            baselines.append(version)
        return baselines


class RegressionDetector:
    """Detects and analyzes quality regressions."""

    def __init__(
        self,
        baseline_manager: Optional[BaselineManager] = None,
        allowed_regression_percent: float = 1.0,  # Allow up to 1% regression
    ):
        """Initialize regression detector.

        Args:
            baseline_manager: BaselineManager instance (creates default if None)
            allowed_regression_percent: Maximum acceptable % regression
        """
        self.baseline_manager = baseline_manager or BaselineManager()
        self.allowed_regression_percent = allowed_regression_percent

    def detect(
        self,
        current_report: ConsolidatedQualityReport,
        baseline_version: str = "v1.0",
    ) -> RegressionAnalysis:
        """Detect regressions against specified baseline.

        Args:
            current_report: ConsolidatedQualityReport to check
            baseline_version: Which baseline to compare against

        Returns:
            RegressionAnalysis with detection results
        """
        baseline = self.baseline_manager.load_baseline(baseline_version)
        if baseline is None:
            return RegressionAnalysis(
                baseline_version=baseline_version,
                current_quality=current_report.overall_quality(),
                baseline_quality=0.0,
                quality_delta=0.0,
                percent_change=0.0,
                is_regression=False,
                diagnostic_notes=[f"Baseline version '{baseline_version}' not found"],
            )

        current_quality = current_report.overall_quality()
        quality_delta = current_quality - baseline.quality_score
        percent_change = (quality_delta / baseline.quality_score * 100) if baseline.quality_score else 0.0

        # Detect phase-level regressions
        current_phases = current_report.evaluation_suite.quality_scores()
        phase_regressions = {}
        for phase, current_score in current_phases.items():
            baseline_score = baseline.phase_scores.get(phase, 0.0)
            delta = current_score - baseline_score
            if delta < 0:  # Only track regressions
                phase_regressions[phase] = delta

        # Determine if regression is significant
        is_regression = quality_delta < -0.001  # Small epsilon for float comparison
        is_significant_regression = abs(percent_change) > self.allowed_regression_percent

        diagnostic_notes = []
        if is_regression:
            diagnostic_notes.append(f"Quality decreased by {abs(quality_delta):.4f} ({abs(percent_change):.1f}%)")
        if is_significant_regression:
            diagnostic_notes.append(f"Regression exceeds allowed threshold ({self.allowed_regression_percent}%)")
        if phase_regressions:
            diagnostic_notes.append(f"{len(phase_regressions)} phases have lower quality")

        return RegressionAnalysis(
            baseline_version=baseline_version,
            current_quality=current_quality,
            baseline_quality=baseline.quality_score,
            quality_delta=quality_delta,
            percent_change=percent_change,
            is_regression=is_regression,
            phase_regressions=phase_regressions,
            diagnostic_notes=diagnostic_notes,
        )


class VarianceAnalyzer:
    """Analyzes variance across multiple evaluation runs."""

    def __init__(self, determinism_tolerance: float = 0.0001):
        """Initialize variance analyzer.

        Args:
            determinism_tolerance: Maximum acceptable variance for determinism
        """
        self.determinism_tolerance = determinism_tolerance

    def analyze(
        self,
        quality_scores: List[float],
    ) -> VarianceReport:
        """Analyze variance across quality scores.

        Args:
            quality_scores: List of quality scores from multiple runs

        Returns:
            VarianceReport with statistical analysis
        """
        if not quality_scores:
            return VarianceReport(run_count=0)

        if len(quality_scores) == 1:
            return VarianceReport(
                run_count=1,
                quality_scores=quality_scores,
                mean_quality=quality_scores[0],
                std_dev=0.0,
                variance=0.0,
                min_quality=quality_scores[0],
                max_quality=quality_scores[0],
                is_deterministic=True,
            )

        mean_val = mean(quality_scores)
        std_val = stdev(quality_scores)
        var_val = variance(quality_scores)
        coeff_var = std_val / mean_val if mean_val else 0.0

        # Deterministic if variance is below tolerance
        is_deterministic = var_val < self.determinism_tolerance

        return VarianceReport(
            run_count=len(quality_scores),
            quality_scores=quality_scores,
            mean_quality=mean_val,
            std_dev=std_val,
            variance=var_val,
            min_quality=min(quality_scores),
            max_quality=max(quality_scores),
            coefficient_of_variation=coeff_var,
            is_deterministic=is_deterministic,
            determinism_tolerance=self.determinism_tolerance,
        )


class QualityGateVerifier:
    """Verifies statistical significance of quality improvements."""

    def __init__(self, significance_level: float = 0.05, min_runs: int = 3):
        """Initialize verifier.

        Args:
            significance_level: Statistical significance threshold (default 0.05 = 95% confidence)
            min_runs: Minimum runs required for significance testing
        """
        self.significance_level = significance_level
        self.min_runs = min_runs

    def verify_improvement(
        self,
        baseline_score: float,
        current_scores: List[float],
    ) -> Tuple[bool, str]:
        """Verify that quality improvement is statistically significant.

        Args:
            baseline_score: Baseline quality score
            current_scores: List of current quality scores (multiple runs)

        Returns:
            Tuple of (is_significant, explanation)
        """
        if len(current_scores) < self.min_runs:
            return False, f"Need at least {self.min_runs} runs for significance testing (got {len(current_scores)})"

        current_mean = mean(current_scores)
        current_std = stdev(current_scores)

        # Simple t-test heuristic: difference must be > 2 * std_err
        std_err = current_std / (len(current_scores) ** 0.5)
        difference = current_mean - baseline_score

        # If difference > 1.96 * std_err, significant at 0.05 level (95% confidence)
        is_significant = difference > (1.96 * std_err)

        if is_significant:
            return True, f"Improvement {difference:+.4f} is statistically significant (p < {self.significance_level})"
        else:
            return False, f"Improvement {difference:+.4f} may be due to random variation"


# ---------------------------------------------------------------------------
# Step 17: SRL-profile baseline discipline
# ---------------------------------------------------------------------------

#: The four canonical SRL experiment profiles for A/B tracking.
SRL_PROFILES = (
    "verbal_only",
    "verbal_plus_nominal_ungated",
    "verbal_plus_nominal_gated",
    "verbal_plus_nominal_gated_aligns_with",
)


@dataclass
class SRLProfileBaseline:
    """Per-SRL-profile MEANTIME scores with relation-by-kind deltas.

    Stores enough information to attribute a score change to a specific SRL
    profile and relation kind, so that improvements or regressions can be
    attributed rather than mixed across conditions.
    """

    profile: str
    timestamp: str
    rotation_reason: str
    event_strict_f1: float = 0.0
    event_relaxed_f1: float = 0.0
    relation_strict_f1: float = 0.0
    relation_relaxed_f1: float = 0.0
    # Relation-by-kind scores (e.g. {"has_participant": 0.42, "tlink": 0.18, ...})
    relation_by_kind: Dict[str, float] = field(default_factory=dict)
    determinism_pass: bool = True
    cross_phase_consistency_pass: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "timestamp": self.timestamp,
            "rotation_reason": self.rotation_reason,
            "event_strict_f1": self.event_strict_f1,
            "event_relaxed_f1": self.event_relaxed_f1,
            "relation_strict_f1": self.relation_strict_f1,
            "relation_relaxed_f1": self.relation_relaxed_f1,
            "relation_by_kind": self.relation_by_kind,
            "determinism_pass": self.determinism_pass,
            "cross_phase_consistency_pass": self.cross_phase_consistency_pass,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SRLProfileBaseline":
        return SRLProfileBaseline(**d)

    def relation_kind_delta(self, other: "SRLProfileBaseline") -> Dict[str, float]:
        """Compute per-kind F1 deltas relative to *other* (self minus other)."""
        all_kinds = set(self.relation_by_kind) | set(other.relation_by_kind)
        return {
            kind: self.relation_by_kind.get(kind, 0.0) - other.relation_by_kind.get(kind, 0.0)
            for kind in sorted(all_kinds)
        }


class SRLProfileBaselineManager:
    """Manages locked baseline artifacts for the four SRL experiment profiles.

    Each profile gets its own JSON file under ``baseline_dir/srl_profiles/``.
    Rotation archives the old file with a timestamp suffix and writes a new
    locked baseline.  Rotation must supply an explicit *reason* string; the
    gate rejects empty reasons to prevent silent auto-rotation.
    """

    PROFILES = SRL_PROFILES

    def __init__(self, baseline_dir: Path | str):
        self.baseline_dir = Path(baseline_dir) / "srl_profiles"
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _profile_path(self, profile: str) -> Path:
        return self.baseline_dir / f"{profile}.json"

    def _archive_path(self, profile: str, timestamp: str) -> Path:
        return self.baseline_dir / f"{profile}.{timestamp}.archived.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, baseline: SRLProfileBaseline) -> Path:
        """Write a new locked baseline (no archiving).  Use rotate() for updates."""
        path = self._profile_path(baseline.profile)
        with path.open("w") as fh:
            json.dump(baseline.to_dict(), fh, indent=2)
        return path

    def load(self, profile: str) -> Optional[SRLProfileBaseline]:
        """Load the locked baseline for *profile*, or ``None`` if absent."""
        path = self._profile_path(profile)
        if not path.exists():
            return None
        with path.open() as fh:
            return SRLProfileBaseline.from_dict(json.load(fh))

    def rotate(
        self,
        new_baseline: SRLProfileBaseline,
        reason: str,
    ) -> Tuple[Path, Optional[Path]]:
        """Replace the locked baseline for a profile, archiving the old one.

        Parameters
        ----------
        new_baseline:
            The new ``SRLProfileBaseline`` to lock.
        reason:
            Non-empty human-readable explanation (e.g. "Step 9 fallback
            participants improve relation F1 by +0.03").  Empty reasons are
            rejected to prevent silent rotation.

        Returns
        -------
        (new_path, archived_path)
            ``archived_path`` is ``None`` when no prior baseline existed.
        """
        if not reason.strip():
            raise ValueError(
                "rotate() requires a non-empty reason string. "
                "Document why the baseline is changing before rotating."
            )
        new_baseline.rotation_reason = reason
        new_baseline.timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        archived_path: Optional[Path] = None
        old_path = self._profile_path(new_baseline.profile)
        if old_path.exists():
            old_data = json.loads(old_path.read_text())
            old_ts = old_data.get("timestamp", "unknown")
            archived_path = self._archive_path(new_baseline.profile, old_ts)
            old_path.rename(archived_path)

        new_path = self.save(new_baseline)
        return new_path, archived_path

    def compare(
        self, profile: str, candidate: SRLProfileBaseline
    ) -> Dict[str, Any]:
        """Compare *candidate* against the locked baseline for *profile*.

        Returns a structured dict containing overall deltas and per-kind deltas
        suitable for inclusion in a review bundle.
        """
        locked = self.load(profile)
        if locked is None:
            return {
                "profile": profile,
                "status": "no_baseline",
                "note": f"No locked baseline for profile '{profile}'",
            }
        deltas = candidate.relation_kind_delta(locked)
        overall_relation_delta = (
            candidate.relation_strict_f1 - locked.relation_strict_f1
        )
        overall_event_delta = (
            candidate.event_strict_f1 - locked.event_strict_f1
        )
        regression_kinds = {k: v for k, v in deltas.items() if v < -0.001}
        improvement_kinds = {k: v for k, v in deltas.items() if v > 0.001}
        return {
            "profile": profile,
            "status": "regression" if regression_kinds else "ok",
            "event_strict_f1_delta": overall_event_delta,
            "relation_strict_f1_delta": overall_relation_delta,
            "relation_by_kind_deltas": deltas,
            "regression_kinds": regression_kinds,
            "improvement_kinds": improvement_kinds,
            "determinism_pass": candidate.determinism_pass,
            "cross_phase_consistency_pass": candidate.cross_phase_consistency_pass,
        }

    def list_profiles(self) -> List[str]:
        """Return names of profiles that have a locked baseline."""
        return [p.stem for p in sorted(self.baseline_dir.glob("*.json"))]


def build_review_bundle(
    profile_comparisons: List[Dict[str, Any]],
    variance_report: Optional["VarianceReport"] = None,
    consistency_issues: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble a complete review bundle for the SRL-profile change set.

    This is the single artefact that reviewers check before accepting a
    baseline rotation.  It includes:

    - Per-profile relation-by-kind deltas (from ``SRLProfileBaselineManager.compare``)
    - Determinism verification result
    - Cross-phase consistency issues (from ``CrossPhaseValidator``)
    - Overall pass/fail verdict

    Parameters
    ----------
    profile_comparisons:
        List of dicts returned by ``SRLProfileBaselineManager.compare()``.
    variance_report:
        Optional ``VarianceReport`` from ``VarianceAnalyzer.analyze()``.
    consistency_issues:
        Optional list of issue strings from the cross-phase validator.

    Returns
    -------
    dict suitable for JSON serialisation and CI review.
    """
    any_regression = any(c.get("status") == "regression" for c in profile_comparisons)
    any_det_fail = any(not c.get("determinism_pass", True) for c in profile_comparisons)
    any_consistency_fail = bool(consistency_issues)

    verdict = "PASS"
    if any_regression:
        verdict = "REGRESSION"
    elif any_det_fail:
        verdict = "DETERMINISM_FAIL"
    elif any_consistency_fail:
        verdict = "CONSISTENCY_FAIL"

    bundle: Dict[str, Any] = {
        "verdict": verdict,
        "profile_comparisons": profile_comparisons,
        "consistency_issues": consistency_issues or [],
    }
    if variance_report is not None:
        bundle["variance"] = variance_report.to_dict()
    return bundle

