#!/usr/bin/env python3
"""Reproduce evaluator projection for doc 76437 and list predicted nominal mentions.

Usage:
  PYTHONPATH=. ./.venv/bin/python tools/reproduce_projection_76437.py
"""
from __future__ import annotations

from textgraphx.database.client import make_graph_from_config
from textgraphx.evaluation.meantime_evaluator import build_document_from_neo4j, _mention_attrs_map
import json


def main():
    graph = make_graph_from_config()
    try:
        doc = build_document_from_neo4j(
            graph=graph,
            doc_id=76437,
            gold_token_sequence=None,
            discourse_only=False,
            normalize_nominal_boundaries=True,
            gold_like_nominal_filter=False,
            nominal_profile_mode="all",
        )
    finally:
        try:
            graph.close()
        except Exception:
            pass

    nominals = [m for m in doc.entity_mentions if any(k == 'syntactic_type' and v.upper() in ('NOM','NOMINAL') for k,v in _mention_attrs_map(m).items()) or any(k == 'syntacticType' and v.upper() in ('NOM','NOMINAL') for k,v in _mention_attrs_map(m).items())]

    out = {
        "doc_id": doc.doc_id,
        "total_predicted_entity_mentions": len(doc.entity_mentions),
        "predicted_nominals_count": len(nominals),
        "predicted_nominals": [
            {"span": list(m.span), "attrs": dict(m.attrs)} for m in nominals
        ],
    }

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
