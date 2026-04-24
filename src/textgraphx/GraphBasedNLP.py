"""Compatibility alias for the canonical GraphBasedNLP ingestion module."""

import sys

from textgraphx.pipeline.ingestion import graph_based_nlp as _canonical_graph_based_nlp


if __name__ != "__main__":
    sys.modules[__name__] = _canonical_graph_based_nlp


def main() -> None:
    _canonical_graph_based_nlp.main()


if __name__ == "__main__":
    main()
