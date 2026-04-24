"""Canonical pipeline phase modules."""

__all__ = [
    "EventEnrichmentPhase",
    "TemporalPhase",
]


def __getattr__(name):
    if name == "EventEnrichmentPhase":
        from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

        return EventEnrichmentPhase
    if name == "TemporalPhase":
        from textgraphx.pipeline.phases.temporal import TemporalPhase

        return TemporalPhase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
