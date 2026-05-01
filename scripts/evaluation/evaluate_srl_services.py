#!/usr/bin/env python3
"""Comprehensive service-level evaluation for verbal + nominal SRL APIs.

Usage:
  python scripts/evaluation/evaluate_srl_services.py \
    --dataset scripts/evaluation/data/srl_service_gold_dataset.json
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

VERBAL_URL_DEFAULT = "http://localhost:8010/predict"
NOMINAL_URL_DEFAULT = "http://localhost:8011/predict_nom"
TIMEOUT_SECONDS = 25


def _role_labels_from_tags(tags: List[str]) -> List[str]:
    labels = set()
    for tag in tags or []:
        if tag == "O":
            continue
        if "-" not in tag:
            continue
        _, label = tag.split("-", 1)
        if label == "V":
            continue
        labels.add(label)
    return sorted(labels)


def _normalize_role(role: str) -> str:
    role = (role or "").strip()
    if role.startswith("C-") or role.startswith("R-"):
        role = role[2:]

    if role.startswith("ARG") and "-" in role:
        head = role.split("-", 1)[0]
        if head.startswith("ARG") and len(head) > 3 and head[3:].isdigit():
            return head

    return role


def _percent(numer: int, denom: int) -> float:
    if denom == 0:
        return 0.0
    return (100.0 * numer) / denom


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    idx = (len(vals) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return vals[lo]
    frac = idx - lo
    return vals[lo] + (vals[hi] - vals[lo]) * frac


def _find_by_surface(items: List[Dict], key: str, surface: str) -> Dict | None:
    wanted = (surface or "").strip().lower()
    for item in items or []:
        val = str(item.get(key, "")).strip().lower()
        if val == wanted:
            return item
    return None


def _eval_target(pred_item: Dict | None, required_roles: List[str]) -> Tuple[bool, List[str], List[str]]:
    if pred_item is None:
        return False, required_roles, []
    got = _role_labels_from_tags(pred_item.get("tags") or [])
    missing = [r for r in required_roles if r not in got]
    ok = len(missing) == 0
    return ok, missing, got


def _eval_target_normalized(pred_item: Dict | None, required_roles: List[str]) -> Tuple[bool, List[str], List[str]]:
    if pred_item is None:
        return False, required_roles, []

    got_raw = _role_labels_from_tags(pred_item.get("tags") or [])
    got_norm = sorted({_normalize_role(r) for r in got_raw})
    req_norm = [_normalize_role(r) for r in required_roles]
    missing = [r for r in req_norm if r not in got_norm]
    ok = len(missing) == 0
    return ok, missing, got_norm


def _post_json(url: str, sentence: str) -> Dict:
    response = requests.post(url, json={"sentence": sentence}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def evaluate(dataset: Dict, verbal_url: str, nominal_url: str) -> Dict:
    summary = {
        "strict": {
            "verbal": {"examples": 0, "targets": 0, "targets_passed": 0, "examples_passed": 0},
            "nominal": {"examples": 0, "targets": 0, "targets_passed": 0, "examples_passed": 0},
        },
        "normalized": {
            "verbal": {"examples": 0, "targets": 0, "targets_passed": 0, "examples_passed": 0},
            "nominal": {"examples": 0, "targets": 0, "targets_passed": 0, "examples_passed": 0},
        },
    }
    details = {"verbal": [], "nominal": []}
    latency_ms = {"verbal": [], "nominal": []}
    failure_counts = {
        "strict_missing_roles": {"verbal": {}, "nominal": {}},
        "predicate_not_found": {"verbal": 0, "nominal": 0},
        "role_variant_recoveries": {"verbal": 0, "nominal": 0},
    }

    for mode in ("verbal", "nominal"):
        url = verbal_url if mode == "verbal" else nominal_url
        pred_key = "verbs" if mode == "verbal" else "frames"
        surface_key = "verb" if mode == "verbal" else "predicate"

        for ex in dataset.get(mode, []):
            sentence = ex["sentence"]
            ex_id = ex["id"]
            targets = ex.get("targets", [])
            summary["strict"][mode]["examples"] += 1
            summary["strict"][mode]["targets"] += len(targets)
            summary["normalized"][mode]["examples"] += 1
            summary["normalized"][mode]["targets"] += len(targets)

            try:
                t0 = time.perf_counter()
                response = _post_json(url, sentence)
                latency_ms[mode].append((time.perf_counter() - t0) * 1000.0)
                preds = response.get(pred_key) or []
                ex_error = None
            except Exception as exc:  # noqa: BLE001
                response = {}
                preds = []
                ex_error = str(exc)

            target_rows = []
            example_ok_strict = ex_error is None
            example_ok_normalized = ex_error is None

            for target in targets:
                pred_item = _find_by_surface(preds, surface_key, target.get("surface", ""))
                ok_strict, missing_roles_strict, got_roles_strict = _eval_target(
                    pred_item, target.get("required_roles", [])
                )
                ok_norm, missing_roles_norm, got_roles_norm = _eval_target_normalized(
                    pred_item, target.get("required_roles", [])
                )

                if ok_strict:
                    summary["strict"][mode]["targets_passed"] += 1
                else:
                    example_ok_strict = False
                    for role in missing_roles_strict:
                        role_map = failure_counts["strict_missing_roles"][mode]
                        role_map[role] = role_map.get(role, 0) + 1

                if ok_norm:
                    summary["normalized"][mode]["targets_passed"] += 1
                else:
                    example_ok_normalized = False

                if pred_item is None:
                    failure_counts["predicate_not_found"][mode] += 1

                if (not ok_strict) and ok_norm:
                    failure_counts["role_variant_recoveries"][mode] += 1

                target_rows.append(
                    {
                        "surface": target.get("surface"),
                        "required_roles": target.get("required_roles", []),
                        "found": pred_item is not None,
                        "strict": {
                            "ok": ok_strict,
                            "missing_roles": missing_roles_strict,
                            "got_roles": got_roles_strict,
                        },
                        "normalized": {
                            "ok": ok_norm,
                            "missing_roles": missing_roles_norm,
                            "got_roles": got_roles_norm,
                        },
                        "predicted_frame": None if pred_item is None else pred_item.get("frame"),
                        "predicted_sense": None if pred_item is None else pred_item.get("sense"),
                    }
                )

            if example_ok_strict:
                summary["strict"][mode]["examples_passed"] += 1
            if example_ok_normalized:
                summary["normalized"][mode]["examples_passed"] += 1

            details[mode].append(
                {
                    "id": ex_id,
                    "sentence": sentence,
                    "ok_strict": example_ok_strict,
                    "ok_normalized": example_ok_normalized,
                    "error": ex_error,
                    "targets": target_rows,
                    "raw_predictions": preds,
                }
            )

    latency_summary = {}
    for mode in ("verbal", "nominal"):
        vals = latency_ms[mode]
        latency_summary[mode] = {
            "count": len(vals),
            "mean_ms": round(sum(vals) / len(vals), 3) if vals else 0.0,
            "p50_ms": round(_percentile(vals, 0.50), 3),
            "p90_ms": round(_percentile(vals, 0.90), 3),
            "max_ms": round(max(vals), 3) if vals else 0.0,
        }

    return {
        "summary": summary,
        "details": details,
        "latency_ms": latency_summary,
        "failure_analysis": failure_counts,
    }


def _format_score_line(scores: Dict) -> str:
    ex_p = _percent(scores["examples_passed"], scores["examples"])
    tg_p = _percent(scores["targets_passed"], scores["targets"])
    return (
        f"examples {scores['examples_passed']}/{scores['examples']} ({ex_p:.1f}%), "
        f"targets {scores['targets_passed']}/{scores['targets']} ({tg_p:.1f}%)"
    )


def _build_markdown_report(report: Dict) -> str:
    md: List[str] = []
    meta = report["metadata"]
    summary = report["summary"]
    strict = summary["strict"]
    norm = summary["normalized"]
    failures = report["failure_analysis"]
    latency = report["latency_ms"]

    md.append("# SRL Service Evaluation Report")
    md.append("")
    md.append("## Run Metadata")
    md.append(f"- Timestamp (UTC): {meta['timestamp_utc']}")
    md.append(f"- Dataset: {meta['dataset_path']}")
    md.append(f"- Verbal endpoint: {meta['verbal_url']}")
    md.append(f"- Nominal endpoint: {meta['nominal_url']}")
    md.append(f"- Timeout (s): {meta['timeout_seconds']}")
    md.append(f"- Elapsed (s): {meta['elapsed_seconds']}")
    md.append("")

    md.append("## Score Summary")
    md.append("")
    md.append("### Strict")
    md.append(f"- Verbal: {_format_score_line(strict['verbal'])}")
    md.append(f"- Nominal: {_format_score_line(strict['nominal'])}")
    md.append("")
    md.append("### Normalized (role-variant tolerant)")
    md.append(f"- Verbal: {_format_score_line(norm['verbal'])}")
    md.append(f"- Nominal: {_format_score_line(norm['nominal'])}")
    md.append("")

    md.append("## Latency")
    md.append("")
    for mode in ("verbal", "nominal"):
        lm = latency[mode]
        md.append(
            f"- {mode.capitalize()}: n={lm['count']}, mean={lm['mean_ms']} ms, "
            f"p50={lm['p50_ms']} ms, p90={lm['p90_ms']} ms, max={lm['max_ms']} ms"
        )
    md.append("")

    md.append("## Failure Analysis")
    md.append("")
    for mode in ("verbal", "nominal"):
        md.append(f"### {mode.capitalize()}")
        md.append(f"- Predicate not found targets: {failures['predicate_not_found'][mode]}")
        md.append(f"- Strict failures recovered by normalization: {failures['role_variant_recoveries'][mode]}")
        missing = failures["strict_missing_roles"][mode]
        if missing:
            top = sorted(missing.items(), key=lambda x: x[1], reverse=True)[:10]
            parts = [f"{role}:{count}" for role, count in top]
            md.append(f"- Most frequent missing strict roles: {', '.join(parts)}")
        else:
            md.append("- Most frequent missing strict roles: none")
        md.append("")

    md.append("## Discussion")
    md.append("")
    strict_nom_t = strict["nominal"]["targets"]
    strict_nom_p = strict["nominal"]["targets_passed"]
    norm_nom_p = norm["nominal"]["targets_passed"]
    strict_gap = norm_nom_p - strict_nom_p

    if strict_gap > 0:
        md.append(
            "- Normalized scoring improves nominal results, indicating many strict misses are role-inventory "
            "variant issues (for example ARG1-PRD vs ARG1) rather than true argument extraction failures."
        )
    else:
        md.append(
            "- Normalized scoring does not materially change results, suggesting remaining errors are likely predicate "
            "detection gaps or true role assignment misses."
        )

    if strict_nom_t > 0:
        md.append(
            f"- Nominal strict target recall is {strict_nom_p}/{strict_nom_t}; this is the main improvement area "
            "for production use if strict NomBank role matching is required."
        )

    md.append(
        "- Verbal SRL quality can be interpreted with higher confidence when strict and normalized scores are close, "
        "which indicates role labels already align to expected PropBank schema in this benchmark."
    )
    md.append("")

    md.append("## Per-Example Outcomes")
    md.append("")
    for mode in ("verbal", "nominal"):
        md.append(f"### {mode.capitalize()}")
        for ex in report["details"][mode]:
            status = "PASS" if ex["ok_strict"] else "FAIL"
            status_n = "PASS" if ex["ok_normalized"] else "FAIL"
            md.append(f"- {ex['id']} | strict={status} | normalized={status_n} | {ex['sentence']}")
            if ex["error"]:
                md.append(f"  - error: {ex['error']}")
            for t in ex["targets"]:
                if (not t["strict"]["ok"]) or (not t["normalized"]["ok"]) or (not t["found"]):
                    md.append(
                        "  - target="
                        f"{t['surface']} found={t['found']} strict_missing={t['strict']['missing_roles']} "
                        f"normalized_missing={t['normalized']['missing_roles']}"
                    )
        md.append("")

    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate verbal+nominal SRL services on a gold dataset.")
    parser.add_argument("--dataset", required=True, help="Path to JSON dataset.")
    parser.add_argument("--verbal-url", default=VERBAL_URL_DEFAULT)
    parser.add_argument("--nominal-url", default=NOMINAL_URL_DEFAULT)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    with dataset_path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    started = time.time()
    report = evaluate(dataset, args.verbal_url, args.nominal_url)
    report["metadata"] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "verbal_url": args.verbal_url,
        "nominal_url": args.nominal_url,
        "timeout_seconds": TIMEOUT_SECONDS,
        "dataset_sizes": {
            "verbal_examples": len(dataset.get("verbal", [])),
            "nominal_examples": len(dataset.get("nominal", [])),
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }

    if args.output:
        out_path = Path(args.output)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path("out") / f"srl_service_eval_{stamp}.json"
    md_out_path = out_path.with_suffix(".md")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_out_path.write_text(_build_markdown_report(report), encoding="utf-8")

    verbal_s = report["summary"]["strict"]["verbal"]
    nominal_s = report["summary"]["strict"]["nominal"]
    verbal_n = report["summary"]["normalized"]["verbal"]
    nominal_n = report["summary"]["normalized"]["nominal"]
    print("Evaluation complete")
    print(f"Report: {out_path}")
    print(f"Discussion report: {md_out_path}")
    print(
        "Verbal strict: "
        f"examples {verbal_s['examples_passed']}/{verbal_s['examples']}, "
        f"targets {verbal_s['targets_passed']}/{verbal_s['targets']}"
    )
    print(
        "Nominal strict: "
        f"examples {nominal_s['examples_passed']}/{nominal_s['examples']}, "
        f"targets {nominal_s['targets_passed']}/{nominal_s['targets']}"
    )
    print(
        "Verbal normalized: "
        f"examples {verbal_n['examples_passed']}/{verbal_n['examples']}, "
        f"targets {verbal_n['targets_passed']}/{verbal_n['targets']}"
    )
    print(
        "Nominal normalized: "
        f"examples {nominal_n['examples_passed']}/{nominal_n['examples']}, "
        f"targets {nominal_n['targets_passed']}/{nominal_n['targets']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
