"""Compatibility alias for the canonical SRL enricher skeleton module."""

import sys

from textgraphx.text_processing_components.llm import srl_enricher_skeleton as _canonical_srl_enricher_skeleton


if __name__ != "__main__":
    sys.modules[__name__] = _canonical_srl_enricher_skeleton


def main() -> None:
    _canonical_srl_enricher_skeleton.main()


if __name__ == "__main__":
    main()