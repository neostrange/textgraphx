"""TLINK Gold Pattern Inventory — MEANTIME corpus diagnostic.

Reads all annotated MEANTIME XML files and reports:
  1. relType distribution across all documents
  2. Source/target type breakdown (EVENT-EVENT, EVENT-TIMEX, TIMEX-EVENT, TIMEX-TIMEX)
  3. Signal presence and lexicon
  4. Which current TlinksRecognizer rule_ids (cases 1-11) plausibly cover each gold pattern
  5. Uncovered patterns (precision recall gap)

Usage:
    python scripts/evaluation/tlink_gold_analysis.py

Requirements: standard library only; no Neo4j or spaCy needed.
"""

from __future__ import annotations

import collections
import pathlib
import sys
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Locate annotated corpus
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ANNOTATED_DIR = REPO_ROOT / "src" / "textgraphx" / "datastore" / "annotated"

# ---------------------------------------------------------------------------
# Mapping: what our current rule cases can produce
# ---------------------------------------------------------------------------

CASE_COVERAGE = {
    "case1_after_eventive": {"endpoints": "E-E", "reltypes": {"AFTER"}, "signal_required": True},
    "case2_eventive_complement": {"endpoints": "E-E", "reltypes": {"AFTER", "BEFORE", "VAGUE"}, "signal_required": True},
    "case3_eventive_head": {"endpoints": "E-E", "reltypes": {"AFTER", "BEFORE", "SIMULTANEOUS", "VAGUE"}, "signal_required": True},
    "case4_timex_head_match": {"endpoints": "E-T", "reltypes": {"IS_INCLUDED"}, "signal_required": False},
    "case5_timex_preposition": {"endpoints": "E-T", "reltypes": {"MEASURE", "BEGUN_BY", "AFTER", "IS_INCLUDED", "ENDED_BY", "BEFORE", "VAGUE"}, "signal_required": False},
    "case6_dct_anchor": {"endpoints": "E-DCT", "reltypes": {"AFTER", "IS_INCLUDED", "BEFORE", "VAGUE"}, "signal_required": False},
    "case7_clause_scope_connective": {"endpoints": "E-E", "reltypes": {"BEFORE", "AFTER", "VAGUE"}, "signal_required": True},
    "case8_nombank_dct": {"endpoints": "NOM-DCT", "reltypes": {"IS_INCLUDED"}, "signal_required": False},
    "case9_nombank_sentence_timex": {"endpoints": "NOM-T", "reltypes": {"IS_INCLUDED"}, "signal_required": False},
    "case10_nombank_srl_timex": {"endpoints": "NOM-T", "reltypes": {"IS_INCLUDED"}, "signal_required": False},
    "case11_has_time_anchor": {"endpoints": "E-T", "reltypes": {"IS_INCLUDED"}, "signal_required": False},
}

# All reltypes producible by current system
CURRENT_RELTYPES = set()
for _v in CASE_COVERAGE.values():
    CURRENT_RELTYPES.update(_v["reltypes"])
CURRENT_RELTYPES.discard("VAGUE")

# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _iter_elements(root: ET.Element, tag: str):
    for elem in root.iter():
        if (elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag) == tag:
            yield elem


def _node_type(mid: str, event_ids: set, timex_ids: set) -> str:
    if mid in event_ids:
        return "EVENT"
    if mid in timex_ids:
        return "TIMEX"
    return "UNKNOWN"


def analyze_file(xml_path: pathlib.Path) -> dict:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"  [PARSE ERROR] {xml_path.name}: {exc}", file=sys.stderr)
        return {}

    # Collect EVENT and TIMEX mention ids
    event_ids: set[str] = set()
    timex_ids: set[str] = set()

    for em in _iter_elements(root, "EVENT_MENTION"):
        mid = em.attrib.get("m_id") or em.attrib.get("id")
        if mid:
            event_ids.add(str(mid))

    for tm in _iter_elements(root, "TIMEX3"):
        mid = tm.attrib.get("m_id") or tm.attrib.get("id")
        if mid:
            timex_ids.add(str(mid))

    # Also collect raw EVENT ids (some schemas use EVENT tag)
    for ev in _iter_elements(root, "EVENT"):
        eid = ev.attrib.get("id") or ev.attrib.get("m_id")
        if eid:
            event_ids.add(str(eid))

    tlinks = []
    for tl in _iter_elements(root, "TLINK"):
        # MEANTIME uses lowercase 'reltype'; also accept 'relType' for other corpora
        rel = (
            tl.attrib.get("reltype")
            or tl.attrib.get("relType")
            or "UNKNOWN"
        ).upper()
        signal_id = (
            tl.attrib.get("signalID")
            or tl.attrib.get("signal_id")
            or tl.attrib.get("signalid")
        )
        has_signal = bool(signal_id and signal_id.strip())

        # MEANTIME: source/target are child elements <source m_id="..."/> <target m_id="..."/>
        src_id = None
        tgt_id = None
        for child in tl:
            ctag = child.tag.split("}")[-1] if isinstance(child.tag, str) else child.tag
            if ctag == "source":
                src_id = child.attrib.get("m_id") or src_id
            elif ctag == "target":
                tgt_id = child.attrib.get("m_id") or tgt_id

        # Fallback for other TimeML corpora that use flat attributes
        if src_id is None:
            src_id = (
                tl.attrib.get("eventInstanceID")
                or tl.attrib.get("timeID")
                or tl.attrib.get("lid")
            )
        if tgt_id is None:
            tgt_id = (
                tl.attrib.get("relatedToEventInstance")
                or tl.attrib.get("relatedToTime")
                or tl.attrib.get("related_m_id")
            )

        if not src_id or not tgt_id:
            continue

        src_type = _node_type(str(src_id), event_ids, timex_ids)
        tgt_type = _node_type(str(tgt_id), event_ids, timex_ids)
        endpoint_pair = f"{src_type}-{tgt_type}"

        tlinks.append({
            "reltype": rel,
            "src_id": src_id,
            "tgt_id": tgt_id,
            "src_type": src_type,
            "tgt_type": tgt_type,
            "endpoint_pair": endpoint_pair,
            "has_signal": has_signal,
            "signal_id": signal_id,
        })

    # Collect Signal texts
    signal_texts: list[str] = []
    for sig in _iter_elements(root, "SIGNAL"):
        text = (sig.text or "").strip().lower()
        if text:
            signal_texts.append(text)

    return {
        "file": xml_path.name,
        "n_events": len(event_ids),
        "n_timex": len(timex_ids),
        "n_signals": len(signal_texts),
        "signal_texts": signal_texts,
        "tlinks": tlinks,
    }


def assess_coverage(tlink: dict) -> list[str]:
    """Return list of current case rule_ids that plausibly cover this gold TLINK."""
    rel = tlink["reltype"]
    ep = tlink["endpoint_pair"]
    has_signal = tlink["has_signal"]
    covering = []

    for rule_id, meta in CASE_COVERAGE.items():
        # skip DCT rules for T-T links
        rule_ep = meta["endpoints"]
        rule_reltypes = meta["reltypes"]

        if rel not in rule_reltypes and "VAGUE" not in rule_reltypes:
            continue

        # Rough endpoint match
        if "DCT" in rule_ep:
            if ep not in ("EVENT-TIMEX", "E-DCT"):
                continue
        elif rule_ep == "E-E" and ep != "EVENT-EVENT":
            continue
        elif rule_ep == "E-T" and ep not in ("EVENT-TIMEX",):
            continue
        elif rule_ep.startswith("NOM") and ep not in ("EVENT-TIMEX", "EVENT-EVENT"):
            continue

        # Signal requirement check
        if meta["signal_required"] and not has_signal:
            continue

        covering.append(rule_id)

    return covering


# ---------------------------------------------------------------------------
# Aggregation and reporting
# ---------------------------------------------------------------------------

def main():
    xml_files = sorted(ANNOTATED_DIR.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {ANNOTATED_DIR}")
        sys.exit(1)

    print(f"\n{'='*72}")
    print("TLINK GOLD PATTERN INVENTORY — MEANTIME corpus")
    print(f"{'='*72}\n")

    # Global accumulators
    total_tlinks = 0
    reltype_counts: collections.Counter = collections.Counter()
    endpoint_counts: collections.Counter = collections.Counter()
    signal_lexicon: collections.Counter = collections.Counter()
    uncovered_reltypes: collections.Counter = collections.Counter()
    uncovered_endpoints: collections.Counter = collections.Counter()
    uncovered_total = 0
    covered_total = 0
    rel_endpoint_matrix: collections.Counter = collections.Counter()

    for xml_path in xml_files:
        result = analyze_file(xml_path)
        if not result:
            continue

        tlinks = result["tlinks"]
        print(f"File: {result['file']}")
        print(f"  Events: {result['n_events']}, TIMEX: {result['n_timex']}, Signals: {result['n_signals']}")
        print(f"  TLINKs: {len(tlinks)}")

        if tlinks:
            per_rel: collections.Counter = collections.Counter()
            for tl in tlinks:
                per_rel[tl["reltype"]] += 1
                reltype_counts[tl["reltype"]] += 1
                endpoint_counts[tl["endpoint_pair"]] += 1
                rel_endpoint_matrix[f"{tl['reltype']}|{tl['endpoint_pair']}"] += 1
                total_tlinks += 1

                covering = assess_coverage(tl)
                if not covering:
                    uncovered_reltypes[tl["reltype"]] += 1
                    uncovered_endpoints[tl["endpoint_pair"]] += 1
                    uncovered_total += 1
                else:
                    covered_total += 1

            for rel, cnt in sorted(per_rel.items(), key=lambda x: -x[1]):
                print(f"    {rel:20s}: {cnt}")

        # Signal texts
        for st in result["signal_texts"]:
            signal_lexicon[st] += 1

        print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"{'='*72}")
    print(f"GLOBAL SUMMARY  (total TLINKs: {total_tlinks})")
    print(f"{'='*72}\n")

    print("relType Distribution:")
    for rel, cnt in reltype_counts.most_common():
        pct = 100.0 * cnt / total_tlinks if total_tlinks else 0
        in_current = "✓" if rel in CURRENT_RELTYPES else "✗ NOT IN CURRENT SYSTEM"
        print(f"  {rel:20s}: {cnt:3d} ({pct:5.1f}%)  {in_current}")

    print("\nEndpoint Pair Distribution:")
    for ep, cnt in endpoint_counts.most_common():
        pct = 100.0 * cnt / total_tlinks if total_tlinks else 0
        print(f"  {ep:25s}: {cnt:3d} ({pct:5.1f}%)")

    print("\nRelType × Endpoint Matrix (top 20):")
    for key, cnt in rel_endpoint_matrix.most_common(20):
        rel, ep = key.split("|")
        print(f"  {rel:20s} × {ep:25s}: {cnt}")

    print(f"\nSignal Lexicon (top 20 of {len(signal_lexicon)} unique):")
    for sig, cnt in signal_lexicon.most_common(20):
        print(f"  '{sig}': {cnt}")

    print(f"\nCoverage Analysis:")
    if total_tlinks:
        covered_pct = 100.0 * covered_total / total_tlinks
        uncovered_pct = 100.0 * uncovered_total / total_tlinks
        print(f"  Plausibly covered by existing cases: {covered_total}/{total_tlinks} ({covered_pct:.1f}%)")
        print(f"  NOT covered by existing cases:       {uncovered_total}/{total_tlinks} ({uncovered_pct:.1f}%)")

    if uncovered_reltypes:
        print("\n  Uncovered relType breakdown:")
        for rel, cnt in uncovered_reltypes.most_common():
            print(f"    {rel:20s}: {cnt}")
        print("\n  Uncovered endpoint breakdown:")
        for ep, cnt in uncovered_endpoints.most_common():
            print(f"    {ep:25s}: {cnt}")

    print(f"\n{'='*72}")
    print("RECALL GAP: reltypes absent from current system output:")
    absent = {r for r in reltype_counts if r not in CURRENT_RELTYPES}
    for rel in sorted(absent):
        print(f"  {rel} ({reltype_counts[rel]} gold instances)")
    if not absent:
        print("  (all gold reltypes are in principle producible)")

    print(f"\n{'='*72}\n")


if __name__ == "__main__":
    main()
