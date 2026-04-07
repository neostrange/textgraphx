from pathlib import Path


def test_participant_queries_select_single_best_event_per_frame():
    source = Path("/home/neo/environments/textgraphx/textgraphx/EventEnrichmentPhase.py").read_text(encoding="utf-8")

    # Core participants query should resolve competing frame->event links through
    # a deterministic winner selection rather than fanout over all candidates.
    assert "MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event:TEvent)" in source
    assert "MATCH (f)-[:DESCRIBES]->(event:TEvent)" in source
    assert "ORDER BY rel_priority ASC, distance ASC" in source
    assert "WITH fa, e, head(collect(event)) AS event" in source

    # Non-core participants query should use the same winner strategy.
    assert "WITH fa, head(collect(event)) AS event" in source
