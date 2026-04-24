#!/usr/bin/env python3
from __future__ import annotations
import json
from textgraphx.database.client import make_graph_from_config

def main():
    g = make_graph_from_config()
    rows = g.run("MATCH (a:AnnotatedText) RETURN a.id AS id, a.publicId AS publicId LIMIT 200").data()
    print(json.dumps(rows, indent=2, default=str))
    g.close()

if __name__ == '__main__':
    main()
