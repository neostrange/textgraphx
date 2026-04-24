"""Compatibility alias for the canonical EventEnrichmentPhase module."""

import sys

if __name__ == "__main__" and __package__ is None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from textgraphx.pipeline.phases import event_enrichment as _canonical_event_enrichment


sys.modules[__name__] = _canonical_event_enrichment
