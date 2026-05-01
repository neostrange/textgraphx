"""VerbNet enrichment adapter (non-destructive)

This adapter provides a small, non-destructive enrichment helper that
attaches VerbNet-derived labels and provenance to existing SRL-style
annotations. It never mutates original PropBank fields; instead it
emits a `vn_enrichment` block on each entry describing suggested
changes, decisions, and provenance metadata.

This file is intentionally lightweight so it can be reviewed and
audited before being used in production.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def apply_verbnet_enrichment(
    entries: List[Dict[str, Any]],
    apply_threshold: float = 0.8,
    flag_threshold: float = 0.6,
    min_vn_confidence: float = 0.4,
) -> List[Dict[str, Any]]:
    """Apply non-destructive VerbNet enrichment decisions.

    entries: list of objects in the same format produced by the
      experimental relabeler (contains `non_destructive_spans`).
    The function adds a `vn_enrichment` key to each entry summarizing
    decisions for human-in-the-loop review.

    Returns a new list (shallow-copied) with enrichment metadata added.
    """

    out: List[Dict[str, Any]] = []

    for ent in entries:
        ent_copy = dict(ent)
        spans = ent.get("non_destructive_spans", []) or []
        enrichment: Dict[str, Any] = {"applied": [], "attach_and_flag": [], "attached": []}

        for s in spans:
            alignment = float(s.get("alignment_score") or 0.0)
            vn_conf = float(s.get("vn_confidence") or 0.0)
            original = s.get("original_label")
            suggested = s.get("suggested_label") if s.get("suggested_label") is not None else original

            # Decision logic (non-destructive): prefer conservative checks
            if alignment >= apply_threshold and vn_conf >= min_vn_confidence:
                action = "apply"
                final = suggested
            elif alignment >= flag_threshold:
                action = "attach_and_flag"
                final = original
            else:
                action = "attach"
                final = original

            rec = {
                "span_text": s.get("span", {}).get("text"),
                "original_label": original,
                "suggested_label": suggested,
                "final_label": final,
                "action": action,
                "alignment_score": alignment,
                "vn_confidence": vn_conf,
                "provenance": {
                    "source": s.get("provenance", {}).get("source", "semparse-verbnet-3.x"),
                    "note": "non-destructive enrichment",
                },
            }

            if action == "apply":
                enrichment["applied"].append(rec)
            elif action == "attach_and_flag":
                enrichment["attach_and_flag"].append(rec)
            else:
                enrichment["attached"].append(rec)

        ent_copy["vn_enrichment"] = enrichment
        out.append(ent_copy)

    return out


def add_enrichment_to_file(
    input_path: str,
    output_path: Optional[str] = None,
    apply_threshold: float = 0.8,
    flag_threshold: float = 0.6,
    min_vn_confidence: float = 0.4,
):
    """Load `input_path`, run `apply_verbnet_enrichment`, and write results.

    By default the output_path is the same directory with a suffix.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)

    data = json.load(open(input_path, "r", encoding="utf8"))
    enriched = apply_verbnet_enrichment(data, apply_threshold, flag_threshold, min_vn_confidence)

    if output_path is None:
        base = os.path.basename(input_path).rsplit(".", 1)[0]
        output_path = os.path.join("/tmp", f"{base}.vn_enriched.json")

    with open(output_path, "w", encoding="utf8") as fh:
        json.dump(enriched, fh, indent=2, ensure_ascii=False)

    logger.info("Wrote enriched file: %s", output_path)
    return output_path


def _cli():
    import argparse

    p = argparse.ArgumentParser(description="Non-destructive VerbNet enrichment adapter")
    p.add_argument("input", help="Input JSON (non_destructive_spans format)")
    p.add_argument("--out", help="Output JSON path (default /tmp/<base>.vn_enriched.json)")
    p.add_argument("--apply", type=float, default=0.8, help="apply threshold (alignment_score)")
    p.add_argument("--flag", type=float, default=0.6, help="flag threshold (alignment_score)")
    p.add_argument("--min-vn-conf", type=float, default=0.4, help="minimum VN confidence to auto-apply")
    args = p.parse_args()

    out = add_enrichment_to_file(args.input, args.out, args.apply, args.flag, args.min_vn_conf)
    print("WROTE", out)


if __name__ == "__main__":
    _cli()
