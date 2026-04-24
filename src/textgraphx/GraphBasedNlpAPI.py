"""Compatibility alias for the canonical legacy GraphBasedNLP API module."""

import sys

from textgraphx.infrastructure import graphbased_api as _canonical_graphbased_api


if __name__ != "__main__":
    sys.modules[__name__] = _canonical_graphbased_api


def main() -> None:
    _canonical_graphbased_api.main()


if __name__ == "__main__":
    main()
