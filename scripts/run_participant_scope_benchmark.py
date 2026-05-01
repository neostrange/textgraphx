#!/usr/bin/env python3
"""Run a 3-profile participant-scope benchmark for MEANTIME evaluation.

Profiles:
1. core-only participants (default purity profile)
2. constrained non-core participants (role allowlist, default ARG0/ARG1)
3. full non-core participants (all roles)

The script runs the MEANTIME evaluator three times with identical settings and
prints a concise delta summary relative to core-only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    include_non_core: bool
    non_core_roles: str | None


def _build_env() -> Dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "").strip()
    if not existing:
        env["PYTHONPATH"] = "src"
    elif "src" not in existing.split(":"):
        env["PYTHONPATH"] = f"src:{existing}"
    return env


def _run_profile(
    *,
    repo_root: Path,
    python_bin: str,
    gold_dir: Path,
    output_dir: Path,
    date_tag: str,
    profile: ProfileConfig,
) -> Path:
    stem = f"eval_report_profile_{profile.name}_{date_tag}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    csv_prefix = output_dir / stem

    cmd = [
        python_bin,
        "-m",
        "textgraphx.tools.evaluate_meantime",
        "--gold-dir",
        str(gold_dir),
        "--pred-neo4j",
        "--out-json",
        str(json_path),
        "--out-markdown",
        str(md_path),
        "--export-csv-prefix",
        str(csv_prefix),
    ]

    if profile.include_non_core:
        cmd.append("--include-non-core-participants")
        if profile.non_core_roles:
            cmd.extend(["--non-core-participant-roles", profile.non_core_roles])

    print(f"[run] {profile.name}")
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=_build_env(),
        check=False,
        text=True,
        capture_output=True,
    )

    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout, file=sys.stderr)
        if proc.stderr.strip():
            print(proc.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    return json_path


def _load_metrics(report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    aggr = report["aggregate"]

    rel_strict = aggr["micro"]["strict"]["relation"]
    rel_relaxed = aggr["micro"]["relaxed"]["relation"]
    by_kind_strict = aggr["relation_by_kind"]["micro"]["strict"]
    by_kind_relaxed = aggr["relation_by_kind"]["micro"]["relaxed"]

    return {
        "strict_relation_precision": rel_strict["precision"],
        "strict_relation_recall": rel_strict["recall"],
        "strict_relation_f1": rel_strict["f1"],
        "relaxed_relation_f1": rel_relaxed["f1"],
        "has_participant_strict_precision": by_kind_strict["has_participant"]["precision"],
        "has_participant_strict_recall": by_kind_strict["has_participant"]["recall"],
        "has_participant_strict_f1": by_kind_strict["has_participant"]["f1"],
        "has_participant_strict_tp": by_kind_strict["has_participant"]["tp"],
        "has_participant_strict_fp": by_kind_strict["has_participant"]["fp"],
        "has_participant_strict_fn": by_kind_strict["has_participant"]["fn"],
        "tlink_strict_f1": by_kind_strict["tlink"]["f1"],
        "has_participant_relaxed_f1": by_kind_relaxed["has_participant"]["f1"],
        "scope": report.get("evaluation_scope", {}),
        "projection_determinism": report.get("projection_determinism", {}),
    }


def _print_summary(all_metrics: dict[str, dict]) -> None:
    base = all_metrics["core_only"]

    print("\n=== Absolute Metrics ===")
    for profile_name, metrics in all_metrics.items():
        print(profile_name)
        print(
            "  strict_relation: "
            f"P={metrics['strict_relation_precision']:.6f} "
            f"R={metrics['strict_relation_recall']:.6f} "
            f"F1={metrics['strict_relation_f1']:.6f}"
        )
        print(
            "  has_participant_strict: "
            f"P={metrics['has_participant_strict_precision']:.6f} "
            f"R={metrics['has_participant_strict_recall']:.6f} "
            f"F1={metrics['has_participant_strict_f1']:.6f} "
            f"TP={metrics['has_participant_strict_tp']} "
            f"FP={metrics['has_participant_strict_fp']} "
            f"FN={metrics['has_participant_strict_fn']}"
        )
        print(
            "  tlink_strict_f1: "
            f"{metrics['tlink_strict_f1']:.6f}"
        )

    print("\n=== Delta vs core_only ===")
    for profile_name in ("noncore_arg0_arg1", "noncore_all"):
        metrics = all_metrics[profile_name]
        print(profile_name)
        for key in (
            "strict_relation_precision",
            "strict_relation_recall",
            "strict_relation_f1",
            "relaxed_relation_f1",
            "has_participant_strict_precision",
            "has_participant_strict_recall",
            "has_participant_strict_f1",
            "has_participant_strict_tp",
            "has_participant_strict_fp",
            "has_participant_strict_fn",
            "tlink_strict_f1",
        ):
            delta = metrics[key] - base[key]
            if isinstance(delta, float):
                print(f"  {key}: {delta:+.12f}")
            else:
                print(f"  {key}: {delta:+d}")


def _recommend_profile(all_metrics: dict[str, dict]) -> str:
    # Purity-first policy: maximize strict relation F1, then precision.
    ranking = sorted(
        all_metrics.items(),
        key=lambda item: (
            item[1]["strict_relation_f1"],
            item[1]["strict_relation_precision"],
        ),
        reverse=True,
    )
    return ranking[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 3-way participant-scope benchmark")
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python interpreter to use for evaluator runs.",
    )
    parser.add_argument(
        "--gold-dir",
        default="src/textgraphx/datastore/annotated",
        help="Gold annotation directory used by the evaluator.",
    )
    parser.add_argument(
        "--output-dir",
        default="src/textgraphx/datastore/evaluation/latest",
        help="Directory for generated benchmark evaluation artifacts.",
    )
    parser.add_argument(
        "--date-tag",
        default=datetime.now(timezone.utc).strftime("%Y%m%d"),
        help="Suffix tag for generated report filenames.",
    )
    parser.add_argument(
        "--allowlist-roles",
        default="ARG0,ARG1",
        help="Comma-separated role allowlist used for constrained non-core profile.",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional output path for benchmark summary JSON.",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    gold_dir = (repo_root / args.gold_dir).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = [
        ProfileConfig(name="core_only", include_non_core=False, non_core_roles=None),
        ProfileConfig(name="noncore_arg0_arg1", include_non_core=True, non_core_roles=args.allowlist_roles),
        ProfileConfig(name="noncore_all", include_non_core=True, non_core_roles="all"),
    ]

    report_paths: dict[str, Path] = {}
    for profile in profiles:
        report_paths[profile.name] = _run_profile(
            repo_root=repo_root,
            python_bin=args.python_bin,
            gold_dir=gold_dir,
            output_dir=output_dir,
            date_tag=args.date_tag,
            profile=profile,
        )

    metrics = {name: _load_metrics(path) for name, path in report_paths.items()}
    _print_summary(metrics)

    recommendation = _recommend_profile(metrics)
    print("\n=== Recommendation ===")
    print(f"recommended_profile: {recommendation}")

    summary_payload = {
        "date_tag": args.date_tag,
        "report_paths": {k: str(v) for k, v in report_paths.items()},
        "metrics": metrics,
        "recommended_profile": recommendation,
    }

    summary_json_path = (
        Path(args.summary_json).resolve()
        if args.summary_json
        else output_dir / f"participant_scope_benchmark_summary_{args.date_tag}.json"
    )
    summary_json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"summary_json: {summary_json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
