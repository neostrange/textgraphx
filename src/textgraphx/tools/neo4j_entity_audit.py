#!/usr/bin/env python3
"""Run a set of diagnostic Cypher queries against the local textgraphx Neo4j
instance and write the results to JSON.

This script uses the repository's configuration precedence (environment
variables override file values) via ``textgraphx.neo4j_client.make_graph_from_config``.

Usage:
  ./.venv/bin/python tools/neo4j_entity_audit.py --output audit_output.json
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Dict

from textgraphx.neo4j_client import make_graph_from_config


DEFAULT_OUTPUT = "audit_output.json"


QUERIES: Dict[str, str] = {
    "labels": (
        "MATCH (n) WHERE size(labels(n))>0 UNWIND labels(n) AS lab "
        "RETURN lab AS label, count(*) AS cnt ORDER BY cnt DESC"
    ),
    "frames": "MATCH (f:Frame) RETURN count(f) AS cnt",
    "frame_arguments": "MATCH (fa:FrameArgument) RETURN count(fa) AS cnt",
    "named_entities": "MATCH (ne:NamedEntity) RETURN count(ne) AS cnt",
    "entities": "MATCH (e:Entity) RETURN count(e) AS cnt",
    "entity_mentions": "MATCH (m:EntityMention) RETURN count(m) AS cnt",
    "nominal_mentions": "MATCH (m:NominalMention) RETURN count(m) AS cnt",
    "noun_chunks": "MATCH (nc:NounChunk) RETURN count(nc) AS cnt",
    "event_mentions": "MATCH (ev:EventMention) RETURN count(ev) AS cnt",
    "tag_occurrences": "MATCH (t:TagOccurrence) RETURN count(t) AS cnt",
    "antecedents": "MATCH (a:Antecedent) RETURN count(a) AS cnt",
    "coref_mentions": "MATCH (c:CorefMention) RETURN count(c) AS cnt",
    "participant_rels": (
        "MATCH ()-[r]->() WHERE type(r) IN ['PARTICIPANT','EVENT_PARTICIPANT'] "
        "RETURN type(r) AS rel, count(r) AS cnt"
    ),
    "refers_to": "MATCH ()-[r:REFERS_TO]->() RETURN count(r) AS cnt",
    "in_frame": "MATCH ()-[r:IN_FRAME]->() RETURN count(r) AS cnt",
    "in_mention": "MATCH ()-[r:IN_MENTION]->() RETURN count(r) AS cnt",
    "participates_in": "MATCH ()-[r:PARTICIPATES_IN]->() RETURN count(r) AS cnt",
    "coref_rels": "MATCH ()-[r:COREF]->() RETURN count(r) AS cnt",
    # FrameArguments that do not have an outgoing REFERS_TO or PARTICIPANT link
    "unresolved_frame_arguments_count": (
        "MATCH (fa:FrameArgument) WHERE NOT (fa)-[:REFERS_TO]->() "
        "AND NOT (fa)-[:PARTICIPANT]->() RETURN count(fa) AS cnt"
    ),
    "unresolved_frame_arguments_sample": (
        "MATCH (fa:FrameArgument) WHERE NOT (fa)-[:REFERS_TO]->() "
        "AND NOT (fa)-[:PARTICIPANT]->() RETURN id(fa) AS id, labels(fa) AS labels, properties(fa) AS props LIMIT 50"
    ),
    "duplicated_named_entity_uids": (
        "MATCH (ne:NamedEntity) WHERE ne.uid IS NOT NULL "
        "WITH ne.uid AS uid, count(ne) AS cnt, collect(id(ne)) AS ids "
        "WHERE cnt > 1 RETURN uid, cnt, ids LIMIT 200"
    ),
    "sample_frames": "MATCH (f:Frame) RETURN id(f) AS id, labels(f) AS labels, properties(f) AS props LIMIT 20",
    "sample_named_entities": (
        "MATCH (ne:NamedEntity) RETURN id(ne) AS id, labels(ne) AS labels, properties(ne) AS props LIMIT 50"
    ),
    "participant_provenance_breakdown": (
        "MATCH ()-[r:PARTICIPANT]->() RETURN r.rule_id AS rule_id, r.evidence_source AS source, count(r) AS cnt "
        "ORDER BY cnt DESC LIMIT 200"
    ),
}


def run_queries(graph):
    out = {}
    for name, q in QUERIES.items():
        try:
            rows = graph.run(q).data()
            out[name] = rows
        except Exception as e:
            out[name] = {"error": str(e), "traceback": traceback.format_exc()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="TextGraphX Neo4j entity audit")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="Output JSON file path")
    args = parser.parse_args(argv)

    try:
        graph = make_graph_from_config()
    except Exception as e:
        print("ERROR: could not create Neo4j graph from config:", e, file=sys.stderr)
        print("Check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD or repo config.ini", file=sys.stderr)
        sys.exit(2)

    try:
        res = run_queries(graph)
        with open(args.output, "w") as f:
            json.dump(res, f, indent=2, default=str)
        print("Wrote audit JSON to", args.output)
    finally:
        try:
            graph.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
