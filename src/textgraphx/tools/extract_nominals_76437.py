#!/usr/bin/env python3
"""Extract nominal mentions for a specific document (76437) and print key properties.

Usage:
  PYTHONPATH=. ./.venv/bin/python tools/extract_nominals_76437.py --doc 76437 --output tools/nominals_76437.json
"""
from __future__ import annotations

import argparse
import json
import sys
from textgraphx.neo4j_client import make_graph_from_config


DEFAULT_OUTPUT = "tools/nominals_76437.json"


QUERY = r"""
MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:IN_MENTION]->(m)
WHERE toLower(coalesce(m.syntactic_type, m.syntacticType, '')) IN ['nom','nominal']
WITH DISTINCT m
RETURN id(m) AS node_id,
       labels(m) AS labels,
       coalesce(m.value, m.text, '') AS value,
       coalesce(m.head, '') AS head,
       m.nominalSemanticHead AS nominalSemanticHead,
       m.nominalSemanticHeadTokenIndex AS nominalSemanticHeadTokenIndex,
       coalesce(m.nominalEventiveByWordNet, false) AS nominalEventiveByWordNet,
       coalesce(m.syntactic_type, m.syntacticType, '') AS syntactic_type,
       m.token_id AS token_id,
       properties(m) AS props
"""


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--doc", required=True, help="Document id (e.g. 76437)")
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    args = p.parse_args(argv)

    try:
        graph = make_graph_from_config()
    except Exception as e:
        print("ERROR creating Neo4j graph from config:", e, file=sys.stderr)
        sys.exit(2)

    # Coerce numeric doc id to int so it matches AnnotatedText.id numeric field when present.
    doc_param = args.doc
    if isinstance(doc_param, str) and doc_param.isdigit():
        doc_param = int(doc_param)

    rows = graph.run(QUERY, {"doc_id": doc_param}).data()
    out = {"doc_id": str(args.doc), "count": len(rows), "rows": rows}

    # Print simple table
    if rows:
        header = ["node_id", "value", "head", "nominalSemanticHead", "nominalSemanticHeadTokenIndex", "nominalEventiveByWordNet", "syntactic_type", "token_id"]
        print("\t".join(header))
        for r in rows:
            print(
                "\t".join(
                    str(r.get(h) if r.get(h) is not None else "") for h in header
                )
            )
    else:
        print("No nominal mentions matched for doc", args.doc)

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("Wrote JSON to", args.output)


if __name__ == "__main__":
    main()
