"""Canonical pipeline phase modules."""

__all__ = ["EventEnrichmentPhase"]


def __getattr__(name):
    if name == "EventEnrichmentPhase":
        from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

        return EventEnrichmentPhase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
