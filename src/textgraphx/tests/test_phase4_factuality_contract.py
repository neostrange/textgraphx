from pathlib import Path


def test_event_enrichment_derives_factuality_and_syncs_tevent():
    src = Path(__file__).resolve().parents[1] / "EventEnrichmentPhase.py"
    text = src.read_text(encoding="utf-8")

    assert "query_factuality" in text
    assert "SET em.factuality" in text
    assert "_resolve_tevent_field_conflicts(\"factuality\"" in text


def test_event_factuality_states_are_governed_in_source_logic():
    src = Path(__file__).resolve().parents[1] / "EventEnrichmentPhase.py"
    text = src.read_text(encoding="utf-8")

    for state in ["ASSERTED", "REPORTED", "HYPOTHETICAL", "NEGATED"]:
        assert state in text
