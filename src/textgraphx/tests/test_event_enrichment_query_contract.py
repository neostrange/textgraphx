from pathlib import Path


EEP_SRC = Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"


def test_participant_queries_select_single_best_event_per_frame():
    source = EEP_SRC.read_text(encoding="utf-8")

    # Core participants query should resolve competing frame->event links through
    # a deterministic winner selection rather than fanout over all candidates.
    assert "OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)" in source
    assert "OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)" in source
    assert "coalesce(event_c, event_l) AS event" in source
    assert "ORDER BY rel_priority ASC, distance ASC" in source
    assert "WITH fa, e, head(collect(event)) AS event" in source

    # Non-core participants query should use the same winner strategy.
    assert "WITH fa, head(collect(event)) AS event" in source
