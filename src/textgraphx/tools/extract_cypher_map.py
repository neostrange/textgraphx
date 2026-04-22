#!/usr/bin/env python3
"""Extract Cypher query strings from the codebase and emit a CSV mapping to file/line.

It searches for triple-quoted strings that contain common Cypher keywords (MATCH, MERGE, CREATE, RETURN)
and writes a CSV with columns: file,path,line,preview (first 200 chars),kind

Usage:
    python -m textgraphx.tools.extract_cypher_map --out cypher_map.csv
"""
from __future__ import annotations
import re
import csv
import argparse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CYpher_KEYWORDS = re.compile(r"\b(MATCH|MERGE|CREATE|RETURN|UNWIND|WITH|SET)\b", re.I)


def find_triple_strings(path: Path):
    text = path.read_text(encoding="utf8")
    # naive: find triple-quoted blocks
    blocks = []
    for m in re.finditer(r"([ruRU]?\"\"\"|[ruRU]?''' )", text):
        pass


def extract_from_file(path: Path):
    text = path.read_text(encoding="utf8")
    results = []
    # match triple-quoted strings ('''...''' or """..."") with non-greedy
    for m in re.finditer(r"([ruRU]?)(\"\"\"|''')(.*?)\2", text, re.S):
        quote = m.group(2)
        content = m.group(3)
        if CYpher_KEYWORDS.search(content):
            # compute line
            start = m.start(3)
            line = text.count("\n", 0, start) + 1
            preview = " ".join(content.strip().split())[:200]
            results.append((path.as_posix(), line, preview, content))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default='.', help="root to scan")
    p.add_argument("--out", default='cypher_map.csv', help="CSV output path")
    args = p.parse_args()

    root = Path(args.root)
    py_files = list(root.rglob('*.py'))

    rows = []
    for f in py_files:
        try:
            extracted = extract_from_file(f)
        except Exception:
            continue
        for file, line, preview, content in extracted:
            kind = 'cypher'
            rows.append({'file': file, 'line': line, 'preview': preview, 'kind': kind})

    out_path = Path(args.out)
    with out_path.open('w', newline='', encoding='utf8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['file', 'line', 'preview', 'kind'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    logger.info("Wrote %d cypher snippets to %s", len(rows), out_path.resolve())


if __name__ == '__main__':
    main()
