"""Evaluation Dashboard - comprehensive analytics for MEANTIME gold-vs-predicted comparison.

Reads existing evaluation JSON/CSV reports and gold NAF/XML files.
Does NOT modify any pipeline or evaluation code.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import html as _html
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

import streamlit as st
import pandas as pd

try:
    import spacy
    from spacy import displacy
except Exception:
    spacy = None
    displacy = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PKG_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = _PKG_ROOT / "datastore" / "evaluation"
GOLD_DIR = _PKG_ROOT / "datastore" / "annotated"
DATASET_DIR = _PKG_ROOT / "datastore" / "dataset"
ORIGINAL_DIR = _PKG_ROOT / "datastore" / "original_dataset"


def _find_gold_xml(doc_id: str) -> Optional[Path]:
    """Locate the gold-standard annotated XML for a doc_id."""
    for d in [GOLD_DIR, ORIGINAL_DIR, DATASET_DIR]:
        if not d.exists():
            continue
        for p in d.glob(f"*{doc_id}*"):
            if p.suffix in {".xml", ".naf"}:
                return p
    return None


# ---------------------------------------------------------------------------
# Report discovery
# ---------------------------------------------------------------------------

def discover_runs() -> Dict[str, Path]:
    """Return {display_name: json_path} for all evaluation JSON reports."""
    runs = {}
    if not EVAL_DIR.exists():
        return runs
    for p in sorted(EVAL_DIR.rglob("*.json")):
        if "fp_entries" in p.name or "stdout" in p.name:
            continue
        rel = str(p.relative_to(EVAL_DIR))
        runs[rel] = p
    return runs


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Gold parsing (via the existing evaluator, read-only)
# ---------------------------------------------------------------------------

def _parse_gold(path: Path):
    """Parse a gold XML via the existing meantime_evaluator.parse_meantime_xml."""
    try:
        from textgraphx.evaluation.meantime_evaluator import parse_meantime_xml
        return parse_meantime_xml(str(path))
    except Exception:
        return None


def _mention_to_row(m, tok_map: dict, kind_label: str) -> dict:
    attrs = dict(m.attrs)
    text = " ".join(tok_map.get(t, "?") for t in m.span)
    return {
        "Layer": kind_label,
        "Span Tokens": str(list(m.span)),
        "Text": text,
        "Type/Subtype": attrs.get("syntactic_type", attrs.get("type", "")),
        "Attributes": "; ".join(f"{k}={v}" for k, v in sorted(attrs.items())),
    }


def _relation_to_row(r, tok_map: dict) -> dict:
    src_text = " ".join(tok_map.get(t, "?") for t in r.source_span)
    tgt_text = " ".join(tok_map.get(t, "?") for t in r.target_span)
    attrs = dict(r.attrs)
    return {
        "Relation Kind": r.kind.upper(),
        "Source": f"{r.source_kind}:{src_text}",
        "Source Span": str(list(r.source_span)),
        "Target": f"{r.target_kind}:{tgt_text}",
        "Target Span": str(list(r.target_span)),
        "Attributes": "; ".join(f"{k}={v}" for k, v in sorted(attrs.items())),
    }


# ---------------------------------------------------------------------------
# Helper: enrich examples with token text
# ---------------------------------------------------------------------------

def _example_span_text(span_list: list, tok_map: dict) -> str:
    return " ".join(tok_map.get(int(t), "?") for t in span_list)


def _enrich_example(ex: dict, tok_map: dict) -> dict:
    row: Dict[str, Any] = {}
    if "gold" in ex and isinstance(ex["gold"], dict):
        g = ex["gold"]
        row["Gold Text"] = _example_span_text(g.get("span", []), tok_map)
        row["Gold Span"] = str(g.get("span", []))
        row["Gold Attrs"] = str(g.get("attrs", {}))
    if "predicted" in ex and isinstance(ex["predicted"], dict):
        p = ex["predicted"]
        row["Pred Text"] = _example_span_text(p.get("span", []), tok_map)
        row["Pred Span"] = str(p.get("span", []))
        row["Pred Attrs"] = str(p.get("attrs", {}))
    if "gold" in ex and isinstance(ex["gold"], str):
        row["Gold (raw)"] = ex["gold"]
    if "predicted" in ex and isinstance(ex["predicted"], str):
        row["Pred (raw)"] = ex["predicted"]
    return row


# ---------------------------------------------------------------------------
# Highlighting helpers
# ---------------------------------------------------------------------------

def _extract_raw_text(naf_path: Path) -> str:
    try:
        tree = ET.parse(str(naf_path))
        raw_el = tree.getroot().find("raw")
        if raw_el is not None and (raw_el.text or "").strip():
            return (raw_el.text or "").strip()
    except Exception:
        pass
    return ""


def _render_highlights(text: str, spans: List[dict]):
    if not spans or not text:
        return
    if spacy is not None and displacy is not None:
        try:
            html_out = displacy.render(
                {"text": text, "ents": spans},
                style="ent",
                manual=True,
                options={"colors": {
                    "TP": "#90ee90",
                    "FP": "#ff8b8b",
                    "FN": "#8bbaff",
                    "BOUNDARY": "#ffd700",
                    "TYPE_MISMATCH": "#dda0dd",
                }},
            )
            st.components.v1.html(html_out, height=min(600, 200 + len(text) // 3), scrolling=True)
            return
        except Exception:
            pass
    # HTML fallback
    normalized = []
    for s in sorted(spans, key=lambda x: (x["start"], x["end"])):
        if not normalized or s["start"] >= normalized[-1][1]:
            normalized.append([s["start"], s["end"], s.get("label", "")])
        else:
            if s["end"] > normalized[-1][1]:
                normalized[-1][1] = s["end"]
    parts = []
    last = 0
    color_map = {"TP": "#d4edda", "FP": "#f8d7da", "FN": "#cce5ff", "BOUNDARY": "#fff3cd", "TYPE_MISMATCH": "#e2d5f1"}
    for start, end, label in normalized:
        parts.append(_html.escape(text[last:start]))
        bg = color_map.get(label, "#f0f0f0")
        parts.append(f'<span style="background:{bg};border-radius:3px;padding:0 2px;" title="{label}">{_html.escape(text[start:end])}</span>')
        last = end
    parts.append(_html.escape(text[last:]))
    blob = "<div style='line-height:1.8;font-family:monospace;white-space:pre-wrap;'>" + "".join(parts) + "</div>"
    st.markdown(blob, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CUSTOM_CSS = """
<style>
    div[data-testid="stMetric"] { background: #f8f9fa; border-radius: 8px; padding: 0.5rem; border: 1px solid #e9ecef; }
    .legend-box { display: inline-block; padding: 2px 8px; border-radius: 4px; margin-right: 6px; font-size: 0.85rem; }
</style>
"""


# ===================================================================
# MAIN RENDER FUNCTION
# ===================================================================

def render_eval_page() -> None:
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    runs = discover_runs()
    if not runs:
        st.warning("No evaluation reports found in " + str(EVAL_DIR))
        return

    # ---- Sidebar: Run selector ----
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Evaluation Settings")
    run_names = list(runs.keys())
    selected_run = st.sidebar.selectbox("Evaluation Run", run_names, index=0)
    report = _load_json(runs[selected_run])

    is_batch = report.get("mode") == "batch" or "aggregate" in report

    compare_enabled = st.sidebar.checkbox("Compare with another run")
    compare_run = None
    compare_report = None
    if compare_enabled:
        other_runs = [r for r in run_names if r != selected_run]
        if other_runs:
            compare_run = st.sidebar.selectbox("Compare Run", other_runs, index=0)
            compare_report = _load_json(runs[compare_run])

    eval_mode = st.sidebar.radio("Matching Mode", ["strict", "relaxed"], index=0)

    # ---- Extract data ----
    if is_batch:
        agg = report.get("aggregate", {})
        micro = agg.get("micro", {}).get(eval_mode, {})
        macro = agg.get("macro", {}).get(eval_mode, {})
        rel_by_kind = agg.get("relation_by_kind", {}).get("micro", {}).get(eval_mode, {})
        per_doc_reports = report.get("reports", [])
        scorecards = report.get("scorecards")
        diagnostics = report.get("diagnostics", {})
        eval_scope = report.get("evaluation_scope", {})
        proj_det = report.get("projection_determinism", {})
        doc_ids = [str(r.get("doc_id", "?")) for r in per_doc_reports]
    else:
        micro = report.get(eval_mode, {})
        macro = None
        rel_by_kind = report.get("relation_by_kind", {}).get(eval_mode, {}) if "relation_by_kind" in report else {}
        per_doc_reports = [report]
        scorecards = report.get("scorecards")
        diagnostics = report.get("diagnostics", {})
        eval_scope = report.get("evaluation_scope", {})
        proj_det = report.get("projection_determinism", {})
        doc_ids = [str(report.get("doc_id", "?"))]

    counts = None
    if per_doc_reports:
        if len(doc_ids) > 1:
            selected_doc_id = st.sidebar.selectbox("Document", doc_ids, index=0)
        else:
            selected_doc_id = doc_ids[0]
            st.sidebar.markdown(f"**Document:** `{selected_doc_id}`")
        doc_report = next((r for r in per_doc_reports if str(r.get("doc_id")) == str(selected_doc_id)), per_doc_reports[0])
        counts = doc_report.get("counts", {})
    else:
        selected_doc_id = None
        doc_report = {}

    # ================================================================
    # TAB LAYOUT
    # ================================================================
    tabs = st.tabs([
        "Overview",
        "Gold Inventory",
        "Gold vs Predicted Mapping",
        "Error Analysis",
        "Relations",
        "Diagnostics",
        "Run Comparison",
        "In-Text Highlights",
    ])

    # ================================================================
    # TAB 0: OVERVIEW
    # ================================================================
    with tabs[0]:
        st.subheader("Evaluation Overview")

        meta_cols = st.columns(4)
        with meta_cols[0]:
            st.markdown(f"**Run:** `{selected_run}`")
        with meta_cols[1]:
            st.markdown(f"**Mode:** `{eval_mode}`")
        with meta_cols[2]:
            st.markdown(f"**Documents:** `{len(doc_ids)}`")
        with meta_cols[3]:
            if eval_scope:
                nom_mode = eval_scope.get("nominal_profile_mode", "?")
                st.markdown(f"**Nominal Profile:** `{nom_mode}`")

        st.divider()

        # Gold vs Predicted counts
        if counts:
            st.markdown("#### Gold vs Predicted Counts")
            gold_c = counts.get("gold", {})
            pred_c = counts.get("predicted", {})
            layers = sorted(set(list(gold_c.keys()) + list(pred_c.keys())))
            count_rows = []
            for layer in layers:
                gc = gold_c.get(layer, 0)
                pc = pred_c.get(layer, 0)
                ratio = pc / gc if gc > 0 else float("inf") if pc > 0 else 0
                count_rows.append({
                    "Layer": layer.title(),
                    "Gold Count": gc,
                    "Predicted Count": pc,
                    "Ratio (Pred/Gold)": round(ratio, 2),
                    "Over/Under": "Over-generated" if ratio > 1.5 else "Under-generated" if ratio < 0.7 else "Balanced",
                })
            cdf = pd.DataFrame(count_rows)
            st.dataframe(cdf, use_container_width=True, hide_index=True)

            # Visual counts bar
            chart_counts = pd.DataFrame({
                "Gold": {r["Layer"]: r["Gold Count"] for r in count_rows},
                "Predicted": {r["Layer"]: r["Predicted Count"] for r in count_rows},
            })
            st.bar_chart(chart_counts)

        st.divider()

        # Per-layer metrics table
        st.markdown("#### Per-Layer Metrics (Micro)")
        metric_layers = ["entity", "event", "timex", "relation"]
        metric_rows = []
        for layer in metric_layers:
            m = micro.get(layer, {})
            if not m:
                continue
            metric_rows.append({
                "Layer": layer.title(),
                "TP": m.get("tp", 0),
                "FP": m.get("fp", 0),
                "FN": m.get("fn", 0),
                "Precision": round(m.get("precision", 0), 4),
                "Recall": round(m.get("recall", 0), 4),
                "F1": round(m.get("f1", 0), 4),
            })
        if metric_rows:
            mdf = pd.DataFrame(metric_rows)
            st.dataframe(mdf, use_container_width=True, hide_index=True)
            chart_df = mdf[["Layer", "Precision", "Recall", "F1"]].set_index("Layer")
            st.bar_chart(chart_df)

        if macro:
            st.markdown("#### Per-Layer Metrics (Macro - Document-Averaged)")
            macro_rows = []
            for layer in metric_layers:
                m = macro.get(layer, {})
                if not m:
                    continue
                macro_rows.append({
                    "Layer": layer.title(),
                    "Precision": round(m.get("precision", 0), 4),
                    "Recall": round(m.get("recall", 0), 4),
                    "F1": round(m.get("f1", 0), 4),
                })
            if macro_rows:
                st.dataframe(pd.DataFrame(macro_rows), use_container_width=True, hide_index=True)

        # Scorecards
        if scorecards:
            st.divider()
            st.markdown("#### Scorecards")
            sc_cols = st.columns(2)
            tml = scorecards.get("time_ml_compliance", {})
            if tml:
                with sc_cols[0]:
                    st.markdown("**TimeML Compliance**")
                    st.metric("Composite", f"{tml.get('composite', 0):.3f}")
                    st.caption(f"Event F1: {tml.get('strict_event_f1', 0):.3f} | "
                               f"Timex F1: {tml.get('strict_timex_f1', 0):.3f} | "
                               f"Relation F1: {tml.get('strict_relation_f1', 0):.3f}")
            btr = scorecards.get("beyond_timeml_reasoning", {})
            if btr:
                with sc_cols[1]:
                    st.markdown("**Beyond-TimeML Reasoning**")
                    st.metric("Composite", f"{btr.get('composite', 0):.3f}")
                    st.caption(f"Event Gain: {btr.get('event_gain', 0):.3f} | "
                               f"Relation Gain: {btr.get('relation_gain', 0):.3f}")

        # Projection determinism
        if proj_det:
            st.divider()
            stable = proj_det.get("all_stable") or proj_det.get("deterministic")
            det_runs = proj_det.get("runs", "?")
            det_icon = "✅" if stable else "⚠️"
            st.markdown(f"#### Projection Determinism {det_icon}")
            st.caption(f"Checked over {det_runs} runs - {'Stable' if stable else 'Unstable'}")

    # ================================================================
    # TAB 1: GOLD INVENTORY
    # ================================================================
    with tabs[1]:
        st.subheader(f"Gold Standard Inventory - Doc {selected_doc_id}")

        gold_path = _find_gold_xml(str(selected_doc_id))
        if gold_path is None:
            st.warning(f"Gold XML not found for doc {selected_doc_id}. Searched annotated/, original_dataset/, dataset/.")
            if counts:
                st.markdown("**Counts from report:**")
                st.json(counts)
        else:
            gold_doc = _parse_gold(gold_path)
            if gold_doc is None or not gold_doc.token_sequence:
                st.warning(f"Could not parse gold annotations from {gold_path.name}. File may lack Markables.")
                if counts:
                    st.json(counts)
            else:
                tok_map = dict(gold_doc.token_sequence)
                st.caption(f"Source: `{gold_path.name}` | Tokens: {len(gold_doc.token_sequence)}")

                with st.expander("Raw Document Text", expanded=False):
                    raw_text = " ".join(tok_map[t] for t in sorted(tok_map.keys()))
                    st.text(raw_text)

                # Entities
                st.markdown("#### Entities")
                ent_rows = [_mention_to_row(m, tok_map, "Entity") for m in sorted(gold_doc.entity_mentions, key=lambda x: x.span)]
                if ent_rows:
                    edf = pd.DataFrame(ent_rows)
                    st.dataframe(edf, use_container_width=True, hide_index=True)
                    type_counts = Counter(r["Type/Subtype"] for r in ent_rows)
                    st.caption("Entity subtypes: " + " | ".join(f"**{k or '(none)'}**: {v}" for k, v in sorted(type_counts.items())))
                else:
                    st.info("No entity mentions in gold.")

                # Events
                st.markdown("#### Events")
                evt_rows = [_mention_to_row(m, tok_map, "Event") for m in sorted(gold_doc.event_mentions, key=lambda x: x.span)]
                if evt_rows:
                    st.dataframe(pd.DataFrame(evt_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No event mentions in gold.")

                # Timex
                st.markdown("#### Temporal Expressions (TIMEX3)")
                tmx_rows = [_mention_to_row(m, tok_map, "Timex") for m in sorted(gold_doc.timex_mentions, key=lambda x: x.span)]
                if tmx_rows:
                    st.dataframe(pd.DataFrame(tmx_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No timex mentions in gold.")

                # Relations
                st.markdown("#### Relations")
                rel_rows = [_relation_to_row(r, tok_map) for r in sorted(gold_doc.relations, key=lambda x: (x.kind, x.source_span))]
                if rel_rows:
                    rdf = pd.DataFrame(rel_rows)
                    st.dataframe(rdf, use_container_width=True, hide_index=True)
                    kind_counts = Counter(r["Relation Kind"] for r in rel_rows)
                    st.caption("Relation kinds: " + " | ".join(f"**{k}**: {v}" for k, v in sorted(kind_counts.items())))
                else:
                    st.info("No relations in gold.")

                # CSV download
                all_gold = ent_rows + evt_rows + tmx_rows
                if all_gold:
                    csv_bytes = pd.DataFrame(all_gold).to_csv(index=False).encode("utf-8")
                    st.download_button("Download Gold Inventory (CSV)", csv_bytes,
                                       file_name=f"gold_inventory_{selected_doc_id}.csv", mime="text/csv")

    # ================================================================
    # TAB 2: PREDICTED VS GOLD MAPPING (ONE-TO-ONE)
    # ================================================================
    with tabs[2]:
        st.subheader(f"Gold <-> Predicted Mapping - Doc {selected_doc_id}")

        doc_mode_data = doc_report.get(eval_mode, {})
        if not doc_mode_data:
            st.info("No per-document detail in this report for the selected mode.")
        else:
            gold_path_mapping = _find_gold_xml(str(selected_doc_id))
            tok_map_m: Dict[int, str] = {}
            if gold_path_mapping:
                gd = _parse_gold(gold_path_mapping)
                if gd and gd.token_sequence:
                    tok_map_m = dict(gd.token_sequence)

            layer_filter = st.selectbox("Layer", ["entity", "event", "timex", "relation"], index=0, key="mapping_layer")
            status_filter = st.multiselect(
                "Error Category",
                ["True Positive", "Boundary Mismatch", "Type Mismatch", "Missing (FN)", "Spurious (FP)"],
                default=["True Positive", "Boundary Mismatch", "Type Mismatch", "Missing (FN)", "Spurious (FP)"],
                key="mapping_status",
            )

            layer_data = doc_mode_data.get(layer_filter, {})
            if not layer_data:
                st.info(f"No data for layer '{layer_filter}' in this report.")
            else:
                mc = st.columns(6)
                with mc[0]:
                    st.metric("TP", layer_data.get("tp", 0))
                with mc[1]:
                    st.metric("FP", layer_data.get("fp", 0))
                with mc[2]:
                    st.metric("FN", layer_data.get("fn", 0))
                with mc[3]:
                    st.metric("Precision", f"{layer_data.get('precision', 0):.3f}")
                with mc[4]:
                    st.metric("Recall", f"{layer_data.get('recall', 0):.3f}")
                with mc[5]:
                    st.metric("F1", f"{layer_data.get('f1', 0):.3f}")

                errors = layer_data.get("errors", {})
                if errors:
                    st.markdown("**Error Breakdown:**")
                    err_cols = st.columns(5)
                    labels = ["boundary_mismatch", "type_mismatch", "missing", "spurious", "endpoint_mismatch"]
                    for i, lbl in enumerate(labels):
                        with err_cols[i]:
                            st.metric(lbl.replace("_", " ").title(), errors.get(lbl, 0))

                # Build one-to-one mapping table
                examples = layer_data.get("examples", {})
                mapping_rows = []

                category_map = {
                    "boundary_mismatch": "Boundary Mismatch",
                    "type_mismatch": "Type Mismatch",
                    "missing": "Missing (FN)",
                    "spurious": "Spurious (FP)",
                }

                for cat_key, cat_label in category_map.items():
                    if cat_label not in status_filter:
                        continue
                    for ex in examples.get(cat_key, []):
                        row = _enrich_example(ex, tok_map_m)
                        row["Category"] = cat_label
                        mapping_rows.append(row)

                tp_count = layer_data.get("tp", 0)
                if tp_count > 0 and "True Positive" in status_filter:
                    st.success(f"**{tp_count} True Positive(s)** - gold and predicted matched exactly ({eval_mode} mode).")

                if mapping_rows:
                    mdf = pd.DataFrame(mapping_rows)
                    preferred_order = ["Category", "Gold Text", "Gold Span", "Gold Attrs",
                                       "Pred Text", "Pred Span", "Pred Attrs",
                                       "Gold (raw)", "Pred (raw)"]
                    cols = [c for c in preferred_order if c in mdf.columns]
                    cols += [c for c in mdf.columns if c not in cols]
                    mdf = mdf[cols]
                    st.dataframe(mdf, use_container_width=True, hide_index=True)

                    csv_bytes = mdf.to_csv(index=False).encode("utf-8")
                    st.download_button(f"Download {layer_filter} mapping (CSV)", csv_bytes,
                                       file_name=f"mapping_{layer_filter}_{selected_doc_id}.csv", mime="text/csv")
                elif not tp_count:
                    st.info("No examples available for the selected filters.")

    # ================================================================
    # TAB 3: ERROR ANALYSIS
    # ================================================================
    with tabs[3]:
        st.subheader("Error Analysis")

        doc_mode_err = doc_report.get(eval_mode, {})
        if not doc_mode_err:
            st.info("No per-document detail available.")
        else:
            gold_path_err = _find_gold_xml(str(selected_doc_id))
            tok_map_err: Dict[int, str] = {}
            if gold_path_err:
                gd_err = _parse_gold(gold_path_err)
                if gd_err and gd_err.token_sequence:
                    tok_map_err = dict(gd_err.token_sequence)

            st.markdown("#### Error Distribution Across Layers")
            err_summary_rows = []
            for layer in ["entity", "event", "timex", "relation"]:
                ld = doc_mode_err.get(layer, {})
                errs = ld.get("errors", {})
                if not errs:
                    continue
                row = {"Layer": layer.title()}
                row.update({k.replace("_", " ").title(): v for k, v in errs.items()})
                err_summary_rows.append(row)
            if err_summary_rows:
                edf = pd.DataFrame(err_summary_rows).fillna(0)
                st.dataframe(edf, use_container_width=True, hide_index=True)
                chart_cols = [c for c in edf.columns if c != "Layer"]
                if chart_cols:
                    st.bar_chart(edf.set_index("Layer")[chart_cols])

            st.divider()
            st.markdown("#### Detailed Error Examples")
            for layer in ["entity", "event", "timex", "relation"]:
                ld = doc_mode_err.get(layer, {})
                examples = ld.get("examples", {})
                if not examples:
                    continue
                total_examples = sum(len(v) for v in examples.values() if isinstance(v, list))
                if total_examples == 0:
                    continue
                with st.expander(f"{layer.title()} - {total_examples} error examples", expanded=False):
                    for cat_key in ["boundary_mismatch", "type_mismatch", "missing", "spurious", "endpoint_mismatch"]:
                        exlist = examples.get(cat_key, [])
                        if not exlist:
                            continue
                        st.markdown(f"**{cat_key.replace('_', ' ').title()}** ({len(exlist)})")
                        rows = [_enrich_example(ex, tok_map_err) for ex in exlist]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ================================================================
    # TAB 4: RELATIONS
    # ================================================================
    with tabs[4]:
        st.subheader("Relation Evaluation Drilldown")

        if rel_by_kind:
            st.markdown("#### Relation Metrics by Kind")
            rkind_rows = []
            for kind in sorted(rel_by_kind.keys()):
                m = rel_by_kind[kind]
                rkind_rows.append({
                    "Kind": kind.upper(),
                    "TP": m.get("tp", 0),
                    "FP": m.get("fp", 0),
                    "FN": m.get("fn", 0),
                    "Precision": round(m.get("precision", 0), 4),
                    "Recall": round(m.get("recall", 0), 4),
                    "F1": round(m.get("f1", 0), 4),
                })
            if rkind_rows:
                rkdf = pd.DataFrame(rkind_rows)
                st.dataframe(rkdf, use_container_width=True, hide_index=True)
                st.bar_chart(rkdf.set_index("Kind")[["Precision", "Recall", "F1"]])
        else:
            doc_rbk = doc_report.get("relation_by_kind", {}).get(eval_mode, {})
            if doc_rbk:
                st.markdown("#### Per-Document Relation Metrics by Kind")
                rkind_rows = []
                for kind in sorted(doc_rbk.keys()):
                    m = doc_rbk[kind]
                    rkind_rows.append({
                        "Kind": kind.upper(),
                        "TP": m.get("tp", 0),
                        "FP": m.get("fp", 0),
                        "FN": m.get("fn", 0),
                        "Precision": round(m.get("precision", 0), 4),
                        "Recall": round(m.get("recall", 0), 4),
                        "F1": round(m.get("f1", 0), 4),
                    })
                if rkind_rows:
                    st.dataframe(pd.DataFrame(rkind_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No relation-by-kind breakdown available in this report.")

        # Relation examples
        doc_rel_examples = doc_report.get(eval_mode, {}).get("relation", {}).get("examples", {})
        if doc_rel_examples:
            st.divider()
            st.markdown("#### Relation Error Examples")
            gold_path_rel = _find_gold_xml(str(selected_doc_id))
            tok_map_rel: Dict[int, str] = {}
            if gold_path_rel:
                gd_rel = _parse_gold(gold_path_rel)
                if gd_rel and gd_rel.token_sequence:
                    tok_map_rel = dict(gd_rel.token_sequence)
            for cat_key in ["endpoint_mismatch", "type_mismatch", "missing", "spurious"]:
                exlist = doc_rel_examples.get(cat_key, [])
                if not exlist:
                    continue
                st.markdown(f"**{cat_key.replace('_', ' ').title()}** ({len(exlist)})")
                rows = [_enrich_example(ex, tok_map_rel) for ex in exlist]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ================================================================
    # TAB 5: DIAGNOSTICS
    # ================================================================
    with tabs[5]:
        st.subheader("Diagnostics & Suggestions")

        if not diagnostics:
            st.info("No diagnostics available in this report.")
        else:
            hotspots = diagnostics.get("hotspot_documents", [])
            if hotspots:
                st.markdown("#### Hotspot Documents (Below F1 Threshold)")
                hrows = []
                for h in hotspots:
                    hrows.append({
                        "Doc ID": h.get("doc_id", "?"),
                        "Avg F1": round(h.get("avg_f1", 0), 4),
                        "Weak Layers": ", ".join(h.get("weak_layers", [])),
                    })
                st.dataframe(pd.DataFrame(hrows), use_container_width=True, hide_index=True)

            issue_totals = diagnostics.get("issue_totals", {})
            if issue_totals:
                st.markdown("#### Issue Totals Across Dataset")
                it_rows = []
                for layer, issues in sorted(issue_totals.items()):
                    row = {"Layer": layer.title()}
                    row.update({k.replace("_", " ").title(): v for k, v in issues.items()})
                    it_rows.append(row)
                if it_rows:
                    st.dataframe(pd.DataFrame(it_rows).fillna(0), use_container_width=True, hide_index=True)

            layer_diags = diagnostics.get("layers", [])
            if layer_diags:
                st.markdown("#### Per-Layer Diagnostics")
                for ld in layer_diags:
                    layer_name = ld.get("layer", "?")
                    f1_val = ld.get("f1", 0)
                    weak = "⚠️" if f1_val < 0.5 else "✅"
                    with st.expander(f"{weak} {layer_name.title()} - F1: {f1_val:.3f}", expanded=False):
                        dcols = st.columns(3)
                        with dcols[0]:
                            st.metric("Precision", f"{ld.get('precision', 0):.3f}")
                        with dcols[1]:
                            st.metric("Recall", f"{ld.get('recall', 0):.3f}")
                        with dcols[2]:
                            st.metric("F1", f"{f1_val:.3f}")
                        errs = ld.get("errors", {})
                        if errs:
                            st.json(errs)

            suggestions = diagnostics.get("suggestions", [])
            if suggestions:
                st.divider()
                st.markdown("#### Actionable Suggestions")
                for s in suggestions:
                    st.markdown(f"- {s}")

            if eval_scope:
                st.divider()
                st.markdown("#### Evaluation Scope Configuration")
                st.json(eval_scope)

    # ================================================================
    # TAB 6: RUN COMPARISON
    # ================================================================
    with tabs[6]:
        st.subheader("Run Comparison")

        if not compare_enabled or compare_report is None:
            st.info("Enable 'Compare with another run' in the sidebar to compare two runs.")
        else:
            st.markdown(f"**Run A:** `{selected_run}` vs **Run B:** `{compare_run}`")

            if is_batch:
                micro_a = report.get("aggregate", {}).get("micro", {}).get(eval_mode, {})
            else:
                micro_a = report.get(eval_mode, {})

            is_batch_b = compare_report.get("mode") == "batch" or "aggregate" in compare_report
            if is_batch_b:
                micro_b = compare_report.get("aggregate", {}).get("micro", {}).get(eval_mode, {})
            else:
                micro_b = compare_report.get(eval_mode, {})

            comp_rows = []
            for layer in ["entity", "event", "timex", "relation"]:
                ma = micro_a.get(layer, {})
                mb = micro_b.get(layer, {})
                f1_a = ma.get("f1", 0)
                f1_b = mb.get("f1", 0)
                delta = f1_b - f1_a
                comp_rows.append({
                    "Layer": layer.title(),
                    "F1 (A)": round(f1_a, 4),
                    "F1 (B)": round(f1_b, 4),
                    "Delta": round(delta, 4),
                    "Direction": "+" if delta > 0.001 else "-" if delta < -0.001 else "=",
                    "P (A)": round(ma.get("precision", 0), 4),
                    "P (B)": round(mb.get("precision", 0), 4),
                    "R (A)": round(ma.get("recall", 0), 4),
                    "R (B)": round(mb.get("recall", 0), 4),
                })
            if comp_rows:
                cdf = pd.DataFrame(comp_rows)
                st.dataframe(cdf, use_container_width=True, hide_index=True)

                chart_data = pd.DataFrame({
                    "Run A": {r["Layer"]: r["F1 (A)"] for r in comp_rows},
                    "Run B": {r["Layer"]: r["F1 (B)"] for r in comp_rows},
                })
                st.bar_chart(chart_data)

            sc_a = report.get("scorecards") or {}
            sc_b = compare_report.get("scorecards") or {}
            if sc_a or sc_b:
                st.divider()
                st.markdown("#### Scorecard Comparison")
                for sc_key, sc_label in [("time_ml_compliance", "TimeML Compliance"), ("beyond_timeml_reasoning", "Beyond-TimeML")]:
                    sa = sc_a.get(sc_key, {})
                    sb = sc_b.get(sc_key, {})
                    if sa or sb:
                        comp_a = sa.get("composite", 0)
                        comp_b = sb.get("composite", 0)
                        delta = comp_b - comp_a
                        arrow = "+" if delta > 0.001 else "-" if delta < -0.001 else "="
                        st.markdown(f"**{sc_label}:** A={comp_a:.3f}, B={comp_b:.3f} ({arrow}{delta:+.3f})")

    # ================================================================
    # TAB 7: IN-TEXT HIGHLIGHTS
    # ================================================================
    with tabs[7]:
        st.subheader(f"In-Text Highlights - Doc {selected_doc_id}")

        gold_path_hl = _find_gold_xml(str(selected_doc_id))
        raw_text = ""
        tok_map_hl: Dict[int, str] = {}

        for d in [DATASET_DIR, GOLD_DIR, ORIGINAL_DIR]:
            if not d.exists():
                continue
            for p in d.glob(f"*{selected_doc_id}*"):
                if p.suffix in {".xml", ".naf"}:
                    raw_text = _extract_raw_text(p)
                    if raw_text:
                        break
            if raw_text:
                break

        if gold_path_hl:
            gd_hl = _parse_gold(gold_path_hl)
            if gd_hl and gd_hl.token_sequence:
                tok_map_hl = dict(gd_hl.token_sequence)
                if not raw_text:
                    raw_text = " ".join(tok_map_hl[t] for t in sorted(tok_map_hl.keys()))

        if not raw_text:
            st.warning("No raw text available for in-text highlighting.")
        else:
            hl_layer = st.selectbox("Highlight Layer", ["entity", "event", "timex"], key="hl_layer")
            hl_mode_data = doc_report.get(eval_mode, {}).get(hl_layer, {})
            hl_examples = hl_mode_data.get("examples", {})

            spans: List[dict] = []

            def _find_in_text(text_fragment: str, label: str):
                if not text_fragment or text_fragment.strip() == "?":
                    return
                pat = re.escape(text_fragment)
                for m in re.finditer(pat, raw_text, flags=re.IGNORECASE):
                    spans.append({"start": m.start(), "end": m.end(), "label": label})

            for cat_key, label in [("boundary_mismatch", "BOUNDARY"), ("type_mismatch", "TYPE_MISMATCH"),
                                    ("missing", "FN"), ("spurious", "FP")]:
                for ex in hl_examples.get(cat_key, []):
                    if isinstance(ex.get("gold"), dict):
                        txt = _example_span_text(ex["gold"].get("span", []), tok_map_hl)
                        _find_in_text(txt, label)
                    if isinstance(ex.get("predicted"), dict):
                        txt = _example_span_text(ex["predicted"].get("span", []), tok_map_hl)
                        _find_in_text(txt, label)

            if spans:
                st.markdown(
                    '**Legend:** '
                    '<span class="legend-box" style="background:#d4edda;">TP</span>'
                    '<span class="legend-box" style="background:#f8d7da;">FP (Spurious)</span>'
                    '<span class="legend-box" style="background:#cce5ff;">FN (Missing)</span>'
                    '<span class="legend-box" style="background:#fff3cd;">Boundary Mismatch</span>'
                    '<span class="legend-box" style="background:#e2d5f1;">Type Mismatch</span>',
                    unsafe_allow_html=True)
                _render_highlights(raw_text, spans)
            else:
                st.info("No spans found for highlighting with the selected layer and mode.")

            with st.expander("Full Document Text", expanded=False):
                st.text(raw_text)
