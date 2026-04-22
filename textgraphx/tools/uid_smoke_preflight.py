"""UID preflight and smoke-ingest helper.

One command to:
1) inspect UID constraint/data readiness,
2) optionally run a small GraphBasedNLP ingestion smoke,
3) print post-smoke UID integrity checks,
4) optionally clean smoke data and staging folders.

Examples:
  python -m textgraphx.tools.uid_smoke_preflight --preflight-only
  python -m textgraphx.tools.uid_smoke_preflight --docs 112579,113219,113227 --run-smoke
  python -m textgraphx.tools.uid_smoke_preflight --docs 112579 --run-smoke --cleanup
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from textgraphx import neo4j_client


def _scalar(graph, query: str, params: Dict | None = None):
    rows = graph.run(query, params or {}).data()
    if not rows:
        return None
    first = rows[0]
    return next(iter(first.values())) if first else None


def _show_preflight(graph):
    constraints = graph.run(
        """
        SHOW CONSTRAINTS
        YIELD name, type, labelsOrTypes, properties
        WHERE any(l IN labelsOrTypes WHERE l IN ['NamedEntity','EntityMention'])
        RETURN name, type, labelsOrTypes, properties
        ORDER BY name
        """
    ).data()
    print("constraints:", constraints)
    print(
        "namedentity_uid_null_or_blank:",
        _scalar(graph, "MATCH (n:NamedEntity) WHERE n.uid IS NULL OR trim(toString(n.uid))='' RETURN count(n) AS c"),
    )
    print(
        "namedentity_uid_duplicate_groups:",
        _scalar(
            graph,
            """
            MATCH (n:NamedEntity)
            WHERE n.uid IS NOT NULL AND trim(toString(n.uid))<>''
            WITH n.uid AS uid, count(*) AS c
            WHERE c > 1
            RETURN count(*) AS g
            """,
        ),
    )
    print(
        "entitymention_uid_null_or_blank:",
        _scalar(graph, "MATCH (m:EntityMention) WHERE m.uid IS NULL OR trim(toString(m.uid))='' RETURN count(m) AS c"),
    )
    print(
        "entitymention_uid_duplicate_groups:",
        _scalar(
            graph,
            """
            MATCH (m:EntityMention)
            WHERE m.uid IS NOT NULL AND trim(toString(m.uid))<>''
            WITH m.uid AS uid, count(*) AS c
            WHERE c > 1
            RETURN count(*) AS g
            """,
        ),
    )


def _cleanup_docs(graph, doc_ids: List[str]):
    queries = [
        "MATCH (n:NamedEntity) WHERE n.token_id STARTS WITH $pfx OR toString(n.id) STARTS WITH $pfx DETACH DELETE n",
        "MATCH (n:EntityMention) WHERE toString(n.doc_id) IN $doc_ids OR toString(n.id) STARTS WITH $pfx OR toString(n.uid) CONTAINS $doc_mid DETACH DELETE n",
        "MATCH (n:FrameArgument) WHERE toString(n.id) STARTS WITH $fa_pfx DETACH DELETE n",
        "MATCH (n:Frame) WHERE toString(n.id) STARTS WITH $frame_pfx DETACH DELETE n",
        "MATCH (n:NounChunk) WHERE toString(n.id) STARTS WITH $pfx DETACH DELETE n",
        "MATCH (n:Antecedent) WHERE toString(n.id) STARTS WITH $ant_pfx DETACH DELETE n",
        "MATCH (n:CorefMention) WHERE toString(n.id) STARTS WITH $coref_pfx DETACH DELETE n",
        "MATCH (n:EventMention) WHERE toString(n.doc_id) IN $doc_ids OR toString(n.token_id) STARTS WITH $pfx DETACH DELETE n",
        "MATCH (n:TEvent) WHERE toString(n.doc_id) IN $doc_ids DETACH DELETE n",
        "MATCH (n:TIMEX) WHERE toString(n.doc_id) IN $doc_ids DETACH DELETE n",
        "MATCH (n:Signal) WHERE toString(n.doc_id) IN $doc_ids DETACH DELETE n",
        "MATCH (n:TagOccurrence) WHERE toString(n.id) STARTS WITH $pfx DETACH DELETE n",
        "MATCH (n:Sentence) WHERE toString(n.id) STARTS WITH $pfx DETACH DELETE n",
        "MATCH (n:AnnotatedText) WHERE toString(n.id) IN $doc_ids DETACH DELETE n",
    ]
    for doc in doc_ids:
        params = {
            "doc_ids": [doc],
            "pfx": f"{doc}_",
            "fa_pfx": f"fa_{doc}_",
            "frame_pfx": f"frame_{doc}_",
            "ant_pfx": f"Antecedent_{doc}_",
            "coref_pfx": f"CorefMention_{doc}_",
            "doc_mid": f"_{doc}_",
        }
        for q in queries:
            graph.run(q, params)


def _stage_docs(repo_root: Path, source_dir: Path, doc_ids: List[str], stage_dir: Path):
    stage_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for doc in doc_ids:
        matches = sorted(source_dir.glob(f"{doc}_*.naf"))
        if not matches:
            raise FileNotFoundError(f"No .naf source found for doc id {doc} in {source_dir}")
        target = stage_dir / matches[0].name
        shutil.copy2(matches[0], target)
        copied.append(target)
    return copied


def _run_smoke_ingest(repo_root: Path, stage_dir: Path, python_bin: str):
    cmd = [
        python_bin,
        "-m",
        "textgraphx.GraphBasedNLP",
        "--dir",
        str(stage_dir),
        "--model",
        "sm",
        "--require-neo4j",
    ]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["TEXTGRAPHX_FAST"] = "1"
    proc = subprocess.run(cmd, cwd=str(repo_root), env=env)
    if proc.returncode != 0:
        raise SystemExit(f"Smoke ingestion failed with exit code {proc.returncode}")


def _show_doc_uid_health(graph, doc_ids: List[str]):
    present = graph.run(
        "MATCH (d:AnnotatedText) WHERE toString(d.id) IN $ids RETURN collect(toString(d.id)) AS ids",
        {"ids": doc_ids},
    ).data()[0]["ids"]
    print("docs_present:", present)
    for doc in doc_ids:
        pfx = f"{doc}_"
        print(
            f"doc={doc}",
            "namedentity_total=",
            _scalar(graph, "MATCH (n:NamedEntity) WHERE n.token_id STARTS WITH $p RETURN count(n) AS c", {"p": pfx}),
            "uid_null_or_blank=",
            _scalar(
                graph,
                "MATCH (n:NamedEntity) WHERE n.token_id STARTS WITH $p AND (n.uid IS NULL OR trim(toString(n.uid))='') RETURN count(n) AS c",
                {"p": pfx},
            ),
            "uid_duplicate_groups=",
            _scalar(
                graph,
                """
                MATCH (n:NamedEntity)
                WHERE n.token_id STARTS WITH $p AND n.uid IS NOT NULL AND trim(toString(n.uid))<>''
                WITH n.uid AS uid, count(*) AS c
                WHERE c > 1
                RETURN count(*) AS g
                """,
                {"p": pfx},
            ),
        )


def main():
    parser = argparse.ArgumentParser(description="UID preflight and smoke-ingest helper")
    parser.add_argument("--docs", default="112579", help="Comma-separated document ids (default: 112579)")
    parser.add_argument(
        "--source-dir",
        default="textgraphx/datastore/dataset-stocks",
        help="Source directory containing NAF files",
    )
    parser.add_argument(
        "--stage-dir",
        default="textgraphx/datastore/tmp-smoke-uid-tool",
        help="Temporary staging directory for smoke docs",
    )
    parser.add_argument(
        "--python-bin",
        default="/home/neo/environments/textgraphx/.venv310/bin/python",
        help="Python interpreter for GraphBasedNLP smoke run",
    )
    parser.add_argument("--preflight-only", action="store_true", help="Only print preflight checks")
    parser.add_argument("--run-smoke", action="store_true", help="Run smoke ingestion on staged docs")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup smoke docs from graph and remove stage dir")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    source_dir = repo_root / args.source_dir
    stage_dir = repo_root / args.stage_dir
    doc_ids = [d.strip() for d in args.docs.split(",") if d.strip()]

    graph = neo4j_client.make_graph_from_config()

    print("=== UID PREFLIGHT ===")
    _show_preflight(graph)

    if args.preflight_only:
        return

    if args.run_smoke:
        print("=== STAGING DOCS ===")
        copied = _stage_docs(repo_root, source_dir, doc_ids, stage_dir)
        print("staged:", [str(p) for p in copied])

        print("=== RUN SMOKE INGEST ===")
        _run_smoke_ingest(repo_root, stage_dir, args.python_bin)

        print("=== POST-SMOKE UID HEALTH ===")
        _show_doc_uid_health(graph, doc_ids)

    if args.cleanup:
        print("=== CLEANUP ===")
        _cleanup_docs(graph, doc_ids)
        if stage_dir.exists():
            shutil.rmtree(stage_dir)
        print("cleanup_done_for_docs:", doc_ids)


if __name__ == "__main__":
    main()
