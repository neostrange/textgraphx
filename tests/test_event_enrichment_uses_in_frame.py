from pathlib import Path


def test_event_enrichment_queries_read_participation_with_in_frame_transition_alias():
    source = Path("/home/neo/environments/textgraphx/textgraphx/EventEnrichmentPhase.py").read_text(encoding="utf-8")

    # Event linkage must include the transitional alias while legacy edges still exist.
    assert "MATCH (f:Frame)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)" in source

    # CLINK and SLINK derivation also rely on token participation reads.
    assert "MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(sub_event:TEvent)" in source
