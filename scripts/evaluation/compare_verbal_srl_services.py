#!/usr/bin/env python3
"""Head-to-head comparison: new transformer-srl vs legacy AllenNLP verbal SRL.

Runs both services on the same verbal gold dataset and reports:
- strict target/example pass rates
- latency (mean/p50/p90/max)
- per-role miss frequencies
- per-example winner comparison
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

NEW_URL_DEFAULT = "http://localhost:8010/predict"
OLD_URL_DEFAULT = "http://localhost:8000/predict"
TIMEOUT_SECONDS = 25


def percentile(values: List[float], p: float) -> float:
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


def roles_from_tags(tags: List[str]) -> List[str]:
    labels = set()
    for tag in tags or []:
        if tag == "O" or "-" not in tag:
            continue
        _, label = tag.split("-", 1)
        if label == "V":
            continue
        labels.add(label)
    return sorted(labels)


def find_predicate(verbs: List[Dict], surface: str) -> Dict | None:
    s = (surface or "").strip().lower()
    for v in verbs or []:
        if str(v.get("verb", "")).strip().lower() == s:
            return v
    return None


def eval_target(pred: Dict | None, required_roles: List[str]) -> Tuple[bool, List[str], List[str]]:
    if pred is None:
        return False, list(required_roles), []
    got = roles_from_tags(pred.get("tags") or [])
    missing = [r for r in required_roles if r not in got]
    return len(missing) == 0, missing, got


def prf_from_counts(tp: int, fp: int, fn: int) -> Dict:
    precision = 0.0 if (tp + fp) == 0 else tp / (tp + fp)
    recall = 0.0 if (tp + fn) == 0 else tp / (tp + fn)
    f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def call_service(url: str, sentence: str) -> Tuple[Dict, float, str | None]:
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json={"sentence": sentence}, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return r.json(), dt_ms, None
    except Exception as exc:  # noqa: BLE001
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return {}, dt_ms, str(exc)


def evaluate_one_service(examples: List[Dict], url: str) -> Dict:
    summary = {"examples": 0, "examples_passed": 0, "targets": 0, "targets_passed": 0}
    details = []
    latencies = []
    miss_counter = Counter()
    predicate_not_found = 0
    tp_total = 0
    fp_total = 0
    fn_total = 0

    for ex in examples:
        summary["examples"] += 1
        summary["targets"] += len(ex.get("targets", []))

        response, latency_ms, error = call_service(url, ex["sentence"])
        latencies.append(latency_ms)
        verbs = response.get("verbs") or []

        ex_ok = error is None
        target_rows = []
        for tgt in ex.get("targets", []):
            pred = find_predicate(verbs, tgt.get("surface", ""))
            ok, missing, got = eval_target(pred, tgt.get("required_roles", []))
            required = set(tgt.get("required_roles", []))
            got_set = set(got)

            tp = len(required & got_set)
            fp = len(got_set - required)
            fn = len(required - got_set)
            tp_total += tp
            fp_total += fp
            fn_total += fn

            if ok:
                summary["targets_passed"] += 1
            else:
                ex_ok = False
                if pred is None:
                    predicate_not_found += 1
                for role in missing:
                    miss_counter[role] += 1

            target_rows.append(
                {
                    "surface": tgt.get("surface"),
                    "required_roles": tgt.get("required_roles", []),
                    "found": pred is not None,
                    "ok": ok,
                    "missing_roles": missing,
                    "got_roles": got,
                }
            )

        if ex_ok:
            summary["examples_passed"] += 1

        details.append(
            {
                "id": ex.get("id"),
                "sentence": ex.get("sentence"),
                "ok": ex_ok,
                "error": error,
                "targets": target_rows,
            }
        )

    latency = {
        "count": len(latencies),
        "mean_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "p50_ms": round(percentile(latencies, 0.5), 3),
        "p90_ms": round(percentile(latencies, 0.9), 3),
        "max_ms": round(max(latencies), 3) if latencies else 0.0,
    }

    return {
        "summary": summary,
        "micro_prf": prf_from_counts(tp_total, fp_total, fn_total),
        "latency_ms": latency,
        "failure_analysis": {
            "predicate_not_found": predicate_not_found,
            "missing_roles": dict(miss_counter),
        },
        "details": details,
    }


def percent(a: int, b: int) -> float:
    return 0.0 if b == 0 else (100.0 * a / b)


def compare_examples(new_details: List[Dict], old_details: List[Dict]) -> Dict:
    by_new = {d["id"]: d for d in new_details}
    by_old = {d["id"]: d for d in old_details}

    new_wins = []
    old_wins = []
    ties = []

    for ex_id in sorted(by_new.keys()):
        n = by_new[ex_id]
        o = by_old.get(ex_id)
        if o is None:
            continue

        n_ok = n["ok"]
        o_ok = o["ok"]
        if n_ok and (not o_ok):
            new_wins.append(ex_id)
        elif o_ok and (not n_ok):
            old_wins.append(ex_id)
        else:
            ties.append(ex_id)

    return {"new_wins": new_wins, "old_wins": old_wins, "ties": ties}


def build_markdown(report: Dict) -> str:
    new = report["new_service"]
    old = report["old_service"]
    cmp_ = report["comparison"]

    ns = new["summary"]
    os = old["summary"]

    md = []
    md.append("# Verbal SRL Head-to-Head")
    md.append("")
    md.append("## Run Metadata")
    md.append(f"- Timestamp (UTC): {report['metadata']['timestamp_utc']}")
    md.append(f"- Dataset: {report['metadata']['dataset_path']}")
    md.append(f"- New service: {report['metadata']['new_url']}")
    md.append(f"- Legacy service: {report['metadata']['old_url']}")
    md.append(f"- Elapsed (s): {report['metadata']['elapsed_seconds']}")
    md.append("")

    md.append("## Quality Summary (Strict)")
    md.append(
        "- New service: "
        f"examples {ns['examples_passed']}/{ns['examples']} ({percent(ns['examples_passed'], ns['examples']):.1f}%), "
        f"targets {ns['targets_passed']}/{ns['targets']} ({percent(ns['targets_passed'], ns['targets']):.1f}%)"
    )
    md.append(
        "- Legacy service: "
        f"examples {os['examples_passed']}/{os['examples']} ({percent(os['examples_passed'], os['examples']):.1f}%), "
        f"targets {os['targets_passed']}/{os['targets']} ({percent(os['targets_passed'], os['targets']):.1f}%)"
    )
    md.append("")

    md.append("## Micro Precision / Recall / F1")
    nprf = new["micro_prf"]
    oprf = old["micro_prf"]
    md.append(
        "- New service: "
        f"P={nprf['precision']:.4f}, R={nprf['recall']:.4f}, F1={nprf['f1']:.4f} "
        f"(TP={nprf['tp']}, FP={nprf['fp']}, FN={nprf['fn']})"
    )
    md.append(
        "- Legacy service: "
        f"P={oprf['precision']:.4f}, R={oprf['recall']:.4f}, F1={oprf['f1']:.4f} "
        f"(TP={oprf['tp']}, FP={oprf['fp']}, FN={oprf['fn']})"
    )
    md.append("")

    md.append("## Latency")
    nlat = new["latency_ms"]
    olat = old["latency_ms"]
    md.append(
        f"- New service: mean={nlat['mean_ms']} ms, p50={nlat['p50_ms']} ms, p90={nlat['p90_ms']} ms, max={nlat['max_ms']} ms"
    )
    md.append(
        f"- Legacy service: mean={olat['mean_ms']} ms, p50={olat['p50_ms']} ms, p90={olat['p90_ms']} ms, max={olat['max_ms']} ms"
    )
    md.append("")

    md.append("## Winner by Example")
    md.append(f"- New-only wins: {len(cmp_['new_wins'])} ({', '.join(cmp_['new_wins']) if cmp_['new_wins'] else 'none'})")
    md.append(f"- Legacy-only wins: {len(cmp_['old_wins'])} ({', '.join(cmp_['old_wins']) if cmp_['old_wins'] else 'none'})")
    md.append(f"- Ties: {len(cmp_['ties'])}")
    md.append("")

    md.append("## Failure Pattern Comparison")
    nmiss = new["failure_analysis"]["missing_roles"]
    omiss = old["failure_analysis"]["missing_roles"]
    md.append(f"- New missing-role counts: {nmiss if nmiss else 'none'}")
    md.append(f"- Legacy missing-role counts: {omiss if omiss else 'none'}")
    md.append("")

    if ns["targets_passed"] > os["targets_passed"]:
        md.append("## Verdict")
        md.append("- Winner: New transformer-srl service (higher strict target accuracy on this benchmark).")
    elif os["targets_passed"] > ns["targets_passed"]:
        md.append("## Verdict")
        md.append("- Winner: Legacy AllenNLP service (higher strict target accuracy on this benchmark).")
    else:
        md.append("## Verdict")
        if nlat["mean_ms"] < olat["mean_ms"]:
            md.append("- Accuracy tie; new transformer-srl wins on latency.")
        elif olat["mean_ms"] < nlat["mean_ms"]:
            md.append("- Accuracy tie; legacy AllenNLP wins on latency.")
        else:
            md.append("- Statistical tie on both strict accuracy and mean latency for this benchmark.")

    md.append("")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare new vs old verbal SRL services.")
    parser.add_argument("--dataset", required=True, help="Path to JSON dataset with verbal section")
    parser.add_argument("--new-url", default=NEW_URL_DEFAULT)
    parser.add_argument("--old-url", default=OLD_URL_DEFAULT)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    verbal = data.get("verbal", [])

    t0 = time.time()
    new_res = evaluate_one_service(verbal, args.new_url)
    old_res = evaluate_one_service(verbal, args.old_url)
    cmp_ = compare_examples(new_res["details"], old_res["details"])

    report = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_path": str(dataset_path),
            "new_url": args.new_url,
            "old_url": args.old_url,
            "timeout_seconds": TIMEOUT_SECONDS,
            "verbal_examples": len(verbal),
            "elapsed_seconds": round(time.time() - t0, 3),
        },
        "new_service": new_res,
        "old_service": old_res,
        "comparison": cmp_,
    }

    if args.output:
        out_json = Path(args.output)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_json = Path("out") / f"verbal_srl_compare_{stamp}.json"

    out_md = out_json.with_suffix(".md")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    out_md.write_text(build_markdown(report), encoding="utf-8")

    ns = report["new_service"]["summary"]
    os = report["old_service"]["summary"]
    nprf = report["new_service"]["micro_prf"]
    oprf = report["old_service"]["micro_prf"]
    print("Comparison complete")
    print(f"JSON report: {out_json}")
    print(f"MD report: {out_md}")
    print(
        "New strict: "
        f"examples {ns['examples_passed']}/{ns['examples']}, targets {ns['targets_passed']}/{ns['targets']}"
    )
    print(
        "Old strict: "
        f"examples {os['examples_passed']}/{os['examples']}, targets {os['targets_passed']}/{os['targets']}"
    )
    print(
        "New micro-PRF: "
        f"P={nprf['precision']:.4f} R={nprf['recall']:.4f} F1={nprf['f1']:.4f} "
        f"(TP={nprf['tp']} FP={nprf['fp']} FN={nprf['fn']})"
    )
    print(
        "Old micro-PRF: "
        f"P={oprf['precision']:.4f} R={oprf['recall']:.4f} F1={oprf['f1']:.4f} "
        f"(TP={oprf['tp']} FP={oprf['fp']} FN={oprf['fn']})"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
