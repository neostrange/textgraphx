"""Detailed entity-level breakdown of MEANTIME strict eval results.

Reads the latest strict eval report and corresponding gold XML files,
resolves t_id spans to text, and prints TP / FP / FN listings plus
aggregate counts per doc, plus FP/FN reason buckets.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "src/textgraphx/datastore/evaluation/latest/eval_report_strict.json"
GOLD_DIR = ROOT / "src/textgraphx/datastore/annotated"


def load_gold_tokens(doc_id: int) -> dict[int, str]:
    for xml in sorted(GOLD_DIR.glob("*.xml")):
        if xml.name.startswith(f"{doc_id}_"):
            root = ET.parse(xml).getroot()
            return {
                int(t.get("t_id")): (t.text or "")
                for t in root.iter()
                if t.tag.split("}")[-1] == "token" and t.get("t_id")
            }
    return {}


def load_gold_entities(doc_id: int) -> list[dict]:
    """Return all gold ENTITY_MENTIONs as {span, syntactic_type, head, text}."""
    out = []
    for xml in sorted(GOLD_DIR.glob("*.xml")):
        if not xml.name.startswith(f"{doc_id}_"):
            continue
        root = ET.parse(xml).getroot()
        toks = {
            int(t.get("t_id")): (t.text or "")
            for t in root.iter()
            if t.tag.split("}")[-1] == "token" and t.get("t_id")
        }
        for m in root.iter():
            if m.tag.split("}")[-1] != "ENTITY_MENTION":
                continue
            ids = sorted(
                int(a.get("t_id"))
                for a in m.findall(".//{*}token_anchor")
                if a.get("t_id") and a.get("t_id").isdigit()
            )
            if not ids:
                continue
            out.append({
                "span": ids,
                "syntactic_type": m.get("syntactic_type", ""),
                "head": m.get("head", ""),
                "text": " ".join(toks.get(t, "?") for t in ids),
            })
        break
    return out


def load_pred_tokens(graph, doc_id: int) -> dict[int, str]:
    """Map TagOccurrence tok_index_doc -> token value for a doc."""
    rows = graph.run(
        """
        MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)
              -[:HAS_TOKEN]->(t:TagOccurrence)
        RETURN t.tok_index_doc AS i, t.text AS v
        """,
        {"doc_id": int(doc_id)},
    ).data()
    return {r["i"]: r["v"] for r in rows if r["i"] is not None}


def span_text(toks: dict[int, str], span: list[int]) -> str:
    if not span:
        return ""
    return " ".join(str(toks.get(t) or "?") for t in span)


def fp_reason(fp_attrs: dict, span: list[int], text: str, gold: list[dict]) -> str:
    """Classify FP by (syntactic_type, span shape).

    NOTE: Predicted t_ids and gold t_ids are NOT in the same coordinate space
    (the evaluator aligns via SequenceMatcher), so we cannot reliably check
    overlap-with-gold from the report. Bucket purely by predicted shape.
    """
    st = (fp_attrs or {}).get("syntactic_type", "?")
    n = len(span)
    if n == 1:
        shape = "singleton"
    elif n <= 3:
        shape = "short"
    elif n <= 6:
        shape = "medium"
    else:
        shape = "long"
    return f"spurious_{st}_{shape}"


def fn_reason(span: list[int], st: str) -> str:
    if len(span) == 1:
        return f"missed_singleton_{st}"
    if len(span) >= 10:
        return f"missed_long_{st}"
    return f"missed_multi_{st}"


def main() -> None:
    from textgraphx.database.client import make_graph_from_config
    graph = make_graph_from_config()
    data = json.loads(EVAL.read_text())
    print(f"# Entity strict-eval breakdown (latest cycle)\n")
    print(f"Aggregate: {data['aggregate']['micro']['strict']['entity']}\n")

    fp_reason_totals: Counter = Counter()
    fn_reason_totals: Counter = Counter()
    type_totals_gold: Counter = Counter()
    type_totals_fp: Counter = Counter()
    type_totals_fn: Counter = Counter()

    for r in sorted(data["reports"], key=lambda x: x["doc_id"]):
        doc_id = r["doc_id"]
        toks = load_gold_tokens(doc_id)
        ptoks = load_pred_tokens(graph, doc_id)
        gold = load_gold_entities(doc_id)
        ent = r["strict"]["entity"]
        ex = ent["examples"]

        print(f"\n{'=' * 78}")
        print(f"DOC {doc_id}  TP={ent['tp']} FP={ent['fp']} FN={ent['fn']} "
              f"P={ent['precision']:.3f} R={ent['recall']:.3f} F1={ent['f1']:.3f}")
        print(f"  errors: {ent['errors']}")
        print(f"  GOLD entity mentions: {len(gold)}")

        # Gold list
        print(f"\n  -- GOLD ({len(gold)}) --")
        for g in gold:
            type_totals_gold[g["syntactic_type"]] += 1
            print(f"    {g['syntactic_type']:8s} span={g['span']}  text={g['text']!r}")

        # TP (derived: gold entries not in `missing`)
        missing_keys = {
            (tuple(m.get("gold", {}).get("span", [])),
             m.get("gold", {}).get("attrs", {}).get("syntactic_type", ""))
            for m in ex.get("missing", [])
        }
        tps = [
            g for g in gold
            if (tuple(g["span"]), g["syntactic_type"]) not in missing_keys
        ]
        print(f"\n  -- TP ({len(tps)}, derived as gold − FN) --")
        for g in tps:
            print(f"    {g['syntactic_type']:8s} span={g['span']}  text={g['text']!r}")

        # FP (spurious)
        sp = ex.get("spurious", [])
        print(f"\n  -- FP ({len(sp)}) --")
        for fp in sp:
            p = fp.get("predicted") or fp.get("pred", {})
            sp_span = p.get("span", [])
            attrs = p.get("attrs", {})
            st = attrs.get("syntactic_type", "?")
            text = span_text(ptoks, sp_span) or "(no text)"
            reason = fp_reason(attrs, sp_span, text, gold)
            fp_reason_totals[reason] += 1
            type_totals_fp[st] += 1
            print(f"    {st:8s} pred_span={sp_span}  text={text!r}  -> {reason}")

        # FN (missing)
        ms = ex.get("missing", [])
        print(f"\n  -- FN ({len(ms)}) --")
        for fn in ms:
            g = fn.get("gold", {})
            g_span = g.get("span", [])
            attrs = g.get("attrs", {})
            st = attrs.get("syntactic_type", "?")
            text = span_text(toks, g_span)
            reason = fn_reason(g_span, st)
            fn_reason_totals[reason] += 1
            type_totals_fn[st] += 1
            print(f"    {st:8s} span={g_span}  text={text!r}  -> {reason}")

        # Boundary mismatches (still count as FN+FP but worth showing)
        bm = ex.get("boundary_mismatch", [])
        if bm:
            print(f"\n  -- boundary_mismatch examples ({len(bm)}) --")
            for b in bm:
                print(f"    {b}")

    # Aggregate stats
    print(f"\n\n{'=' * 78}")
    print("# AGGREGATE STATS\n")
    print("Gold entities by syntactic_type:")
    for k, v in type_totals_gold.most_common():
        print(f"  {k or '(none)':10s} {v}")
    print("\nFalse-positives by syntactic_type:")
    for k, v in type_totals_fp.most_common():
        print(f"  {k or '(none)':10s} {v}")
    print("\nFalse-negatives by syntactic_type:")
    for k, v in type_totals_fn.most_common():
        print(f"  {k or '(none)':10s} {v}")
    print("\nFP reasons:")
    for k, v in fp_reason_totals.most_common():
        print(f"  {k:30s} {v}")
    print("\nFN reasons:")
    for k, v in fn_reason_totals.most_common():
        print(f"  {k:30s} {v}")


if __name__ == "__main__":
    main()
