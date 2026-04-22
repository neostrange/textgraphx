#!/usr/bin/env python3
"""Generate a human-friendly YAML and HTML view of schema/ontology.json.

Usage:
    python -m textgraphx.tools.generate_ontology_human --yaml-out ./ontology.yaml --html-out ./ontology.html

If PyYAML is available the YAML output will be proper YAML; otherwise a JSON-ish fallback is written.
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
import html as _html
import logging

logger = logging.getLogger(__name__)


def load_ontology() -> dict:
    # Prefer package-local schema: textgraphx/schema/ontology.json
    pkg_schema = Path(__file__).resolve().parents[1] / "schema" / "ontology.json"
    repo_schema = Path(__file__).resolve().parents[2] / "schema" / "ontology.json"
    for schema_path in (pkg_schema, repo_schema):
        if schema_path.exists():
            return json.loads(schema_path.read_text(encoding="utf8"))
    raise FileNotFoundError(f"ontology.json not found at {pkg_schema} or {repo_schema}")


def write_yaml(data: dict, out_path: Path) -> None:
    try:
        import yaml  # type: ignore

        out_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf8")
    except Exception:
        # Fallback: write pretty JSON with .yml extension
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf8")


def write_html(data: dict, out_path: Path) -> None:
    parts = []
    parts.append("<html><head><meta charset=\"utf-8\"><title>Ontology</title>")
    parts.append("<style>body{font-family:Arial,Helvetica,sans-serif;margin:24px}pre{background:#f6f8fa;padding:12px;border-radius:6px}</style>")
    parts.append("</head><body>")
    parts.append(f"<h1>Ontology — {data.get('name','schema')}</h1>")

    def render_obj(obj, level=2):
        if isinstance(obj, dict):
            for k, v in obj.items():
                parts.append(f"<h{level}>{_html.escape(str(k))}</h{level}>")
                render_obj(v, min(6, level + 1))
        elif isinstance(obj, list):
            parts.append("<ul>")
            for item in obj:
                parts.append("<li>")
                if isinstance(item, (dict, list)):
                    render_obj(item, min(6, level + 1))
                else:
                    parts.append(_html.escape(str(item)))
                parts.append("</li>")
            parts.append("</ul>")
        else:
            parts.append(f"<pre>{_html.escape(json.dumps(obj, indent=2, ensure_ascii=False))}</pre>")

    render_obj(data)
    parts.append("</body></html>")
    out_path.write_text("\n".join(parts), encoding="utf8")


def main():
    p = argparse.ArgumentParser(description="Generate YAML/HTML from textgraphx/schema/ontology.json")
    p.add_argument("--yaml-out", default="ontology.yaml", help="YAML output path")
    p.add_argument("--html-out", default="ontology.html", help="HTML output path")
    args = p.parse_args()

    data = load_ontology()
    yaml_path = Path(args.yaml_out)
    html_path = Path(args.html_out)

    write_yaml(data, yaml_path)
    write_html(data, html_path)

    logger.info("Wrote YAML -> %s \nWrote HTML -> %s", yaml_path.resolve(), html_path.resolve())


if __name__ == "__main__":
    main()
