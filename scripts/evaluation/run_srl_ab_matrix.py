#!/usr/bin/env python3
"""
SRL A/B matrix evaluation script.

Compares four pipeline configurations against the SRL service gold dataset.

Variant matrix
--------------
V0 — Legacy AllenNLP verbal SRL, no nominal SRL (baseline)
V1 — transformer-srl verbal SRL (port 8010), no nominal SRL
V2 — transformer-srl verbal SRL + CogComp nominal SRL (port 8011)
V3 — V2 + confidence gating (provisional frame filter) + cross-framework fusion

For each variant, the script:
1. Runs SRL prediction against the gold sentence set.
2. Computes token-level F1 (exact match on BIO tags) for verbal and nominal roles.
3. Reports frame coverage, argument density, sense accuracy (when gold roleset is
   provided), and provisional-frame rate.

Usage
-----
    python scripts/evaluation/run_srl_ab_matrix.py [--gold-file PATH] [--output-dir DIR]

Default gold file: scripts/evaluation/data/srl_service_gold_dataset.json
Default output dir: src/textgraphx/datastore/evaluation/baseline/srl_ab_matrix/
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap path so the module runs from any CWD
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

import requests  # noqa: E402  (installed in the venv)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("srl_ab_matrix")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_GOLD_FILE = (
    _REPO_ROOT / "scripts" / "evaluation" / "data" / "srl_service_gold_dataset.json"
)
DEFAULT_OUTPUT_DIR = (
    _REPO_ROOT
    / "src"
    / "textgraphx"
    / "datastore"
    / "evaluation"
    / "baseline"
    / "srl_ab_matrix"
)

VERBAL_URL_TRANSFORMER = "http://localhost:8010/predict"
NOMINAL_URL_COGCOMP = "http://localhost:8011/predict_nom"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class VariantResult:
    variant: str
    description: str
    verbal_precision: float = 0.0
    verbal_recall: float = 0.0
    verbal_f1: float = 0.0
    nominal_precision: float = 0.0
    nominal_recall: float = 0.0
    nominal_f1: float = 0.0
    frame_coverage_per_sentence: float = 0.0
    args_per_frame: float = 0.0
    provisional_rate: float = 0.0
    aligns_with_count: int = 0
    sentences_evaluated: int = 0
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tag-level F1 helpers
# ---------------------------------------------------------------------------

def _bio_to_spans(tags: List[str], words: List[str]) -> List[Tuple[str, str]]:
    """Convert BIO tags to (role, span_text) tuples."""
    spans = []
    current_role = None
    current_tokens: List[str] = []
    for tag, word in zip(tags, words):
        if tag.startswith("B-"):
            if current_role:
                spans.append((current_role, " ".join(current_tokens)))
            current_role = tag[2:]
            current_tokens = [word]
        elif tag.startswith("I-") and current_role:
            current_tokens.append(word)
        else:
            if current_role:
                spans.append((current_role, " ".join(current_tokens)))
                current_role = None
                current_tokens = []
    if current_role:
        spans.append((current_role, " ".join(current_tokens)))
    return spans


def _compute_f1(gold_spans: List[Tuple], pred_spans: List[Tuple]) -> Tuple[float, float, float]:
    gold_set = set(gold_spans)
    pred_set = set(pred_spans)
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


# ---------------------------------------------------------------------------
# Service callers
# ---------------------------------------------------------------------------

def _call_verbal(sentence: str, url: str, timeout: int = 15) -> Optional[dict]:
    try:
        resp = requests.post(url, json={"sentence": sentence}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("verbal SRL call failed: %s", exc)
        return None


def _call_nominal(sentence: str, timeout: int = 15) -> Optional[dict]:
    try:
        resp = requests.post(
            NOMINAL_URL_COGCOMP,
            json={"sentence": sentence},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("nominal SRL call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Variant evaluation logic
# ---------------------------------------------------------------------------

def _evaluate_variant(
    gold_examples: List[dict],
    verbal_url: Optional[str],
    use_nominal: bool,
    confidence_threshold: float = 0.0,
    compute_fusion: bool = False,
) -> VariantResult:
    """
    Run a single variant against the gold examples.

    Parameters
    ----------
    gold_examples:
        List of dicts with keys ``sentence``, ``verbal_gold`` (list of frame
        dicts with ``tags``), and optionally ``nominal_gold``.
    verbal_url:
        URL for verbal SRL. ``None`` means skip verbal.
    use_nominal:
        Whether to call the nominal SRL service.
    confidence_threshold:
        Filter predictions where ``frame_score`` / ``sense_score`` < threshold.
    compute_fusion:
        Whether to count potential ``ALIGNS_WITH`` candidates.
    """
    verbal_p_list: List[float] = []
    verbal_r_list: List[float] = []
    verbal_f1_list: List[float] = []
    nominal_p_list: List[float] = []
    nominal_r_list: List[float] = []
    nominal_f1_list: List[float] = []
    frame_counts: List[int] = []
    arg_counts: List[int] = []
    provisional_frames = 0
    total_frames_with_conf = 0
    aligns_with_candidates = 0
    errors: List[str] = []

    for ex in gold_examples:
        sentence = ex["sentence"]
        words = sentence.split()

        # ---- verbal ----
        if verbal_url:
            resp = _call_verbal(sentence, verbal_url)
            if resp:
                for verb_info in resp.get("verbs", []):
                    conf = verb_info.get("frame_score")
                    if conf is not None:
                        total_frames_with_conf += 1
                        if conf < confidence_threshold:
                            provisional_frames += 1
                            continue  # skip low-confidence in gated variants

                pred_spans: List[Tuple] = []
                num_args = 0
                for verb_info in resp.get("verbs", []):
                    conf = verb_info.get("frame_score", 1.0)
                    if conf is not None and conf < confidence_threshold:
                        continue
                    tags = verb_info.get("tags", [])
                    resp_words = resp.get("words", words)
                    spans = _bio_to_spans(tags, resp_words)
                    pred_spans.extend(spans)
                    num_args += len([s for s in spans if not s[0].startswith("V")])
                frame_counts.append(len(resp.get("verbs", [])))
                arg_counts.append(num_args)

                # Compare against gold if available
                gold_verbal = ex.get("verbal_gold", [])
                gold_spans: List[Tuple] = []
                for gframe in gold_verbal:
                    gold_spans.extend(
                        _bio_to_spans(gframe.get("tags", []), words)
                    )
                if gold_spans:
                    p, r, f1 = _compute_f1(gold_spans, pred_spans)
                    verbal_p_list.append(p)
                    verbal_r_list.append(r)
                    verbal_f1_list.append(f1)

        # ---- nominal ----
        if use_nominal:
            nom_resp = _call_nominal(sentence)
            if nom_resp:
                nom_pred_spans: List[Tuple] = []
                for nom_frame in nom_resp.get("frames", []):
                    conf = nom_frame.get("sense_score")
                    if conf is not None and conf < confidence_threshold:
                        provisional_frames += 1
                        total_frames_with_conf += 1
                        continue
                    if conf is not None:
                        total_frames_with_conf += 1
                    tags = nom_frame.get("tags", [])
                    resp_words = nom_resp.get("words", words)
                    nom_pred_spans.extend(_bio_to_spans(tags, resp_words))

                gold_nominal = ex.get("nominal_gold", [])
                gold_nom_spans: List[Tuple] = []
                for gframe in gold_nominal:
                    gold_nom_spans.extend(
                        _bio_to_spans(gframe.get("tags", []), words)
                    )
                if gold_nom_spans:
                    p, r, f1 = _compute_f1(gold_nom_spans, nom_pred_spans)
                    nominal_p_list.append(p)
                    nominal_r_list.append(r)
                    nominal_f1_list.append(f1)

                if compute_fusion:
                    # Heuristic: count overlapping headwords as candidates
                    nom_headwords = {
                        f.get("predicate", "").lower()
                        for f in nom_resp.get("frames", [])
                    }
                    if verbal_url:
                        v_resp = _call_verbal(sentence, verbal_url) or {}
                        for verb_info in v_resp.get("verbs", []):
                            if verb_info.get("verb", "").lower() in nom_headwords:
                                aligns_with_candidates += 1

    def _mean(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    n = len(gold_examples)
    return VariantResult(
        variant="",
        description="",
        verbal_precision=_mean(verbal_p_list),
        verbal_recall=_mean(verbal_r_list),
        verbal_f1=_mean(verbal_f1_list),
        nominal_precision=_mean(nominal_p_list),
        nominal_recall=_mean(nominal_r_list),
        nominal_f1=_mean(nominal_f1_list),
        frame_coverage_per_sentence=_mean(frame_counts),
        args_per_frame=sum(arg_counts) / max(sum(frame_counts), 1),
        provisional_rate=(
            provisional_frames / total_frames_with_conf
            if total_frames_with_conf else 0.0
        ),
        aligns_with_count=aligns_with_candidates,
        sentences_evaluated=n,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold-file",
        type=Path,
        default=DEFAULT_GOLD_FILE,
        help="Path to gold SRL dataset JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write baseline JSON artifacts.",
    )
    args = parser.parse_args()

    if not args.gold_file.exists():
        logger.error("Gold file not found: %s", args.gold_file)
        return 1

    with args.gold_file.open() as fh:
        gold_examples: List[dict] = json.load(fh)

    logger.info("Loaded %d gold examples from %s", len(gold_examples), args.gold_file)

    variants = [
        ("V0", "Legacy verbal (no framework attr), no nominal", None, False, 0.0, False),
        ("V1", "transformer-srl :8010 verbal only", VERBAL_URL_TRANSFORMER, False, 0.0, False),
        ("V2", "transformer-srl + CogComp nominal", VERBAL_URL_TRANSFORMER, True, 0.0, False),
        ("V3", "V2 + confidence gating (>0.5) + fusion candidates", VERBAL_URL_TRANSFORMER, True, 0.5, True),
    ]

    results: List[VariantResult] = []
    for variant_id, description, verbal_url, use_nominal, threshold, fusion in variants:
        logger.info("Running variant %s: %s", variant_id, description)
        t0 = time.monotonic()
        result = _evaluate_variant(
            gold_examples=gold_examples,
            verbal_url=verbal_url,
            use_nominal=use_nominal,
            confidence_threshold=threshold,
            compute_fusion=fusion,
        )
        result.variant = variant_id
        result.description = description
        elapsed = time.monotonic() - t0
        logger.info(
            "  %s done in %.1fs — verbal_F1=%.3f nominal_F1=%.3f provisional_rate=%.2f",
            variant_id, elapsed,
            result.verbal_f1, result.nominal_f1, result.provisional_rate,
        )
        results.append(result)

    # Write output
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.output_dir / "ab_matrix_results.json"
    with out_file.open("w") as fh:
        json.dump([asdict(r) for r in results], fh, indent=2)
    logger.info("Results written to %s", out_file)

    # Print summary table
    print("\n=== SRL A/B Matrix ===")
    print(f"{'Variant':<6} {'Verbal F1':>10} {'Nominal F1':>11} {'Prov%':>6} {'ALIGNS':>7}  Description")
    print("-" * 75)
    for r in results:
        print(
            f"{r.variant:<6} {r.verbal_f1:>10.3f} {r.nominal_f1:>11.3f} "
            f"{r.provisional_rate * 100:>5.1f}% {r.aligns_with_count:>7}  {r.description}"
        )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
