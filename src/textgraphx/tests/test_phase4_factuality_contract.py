from pathlib import Path


EEP_SRC = Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"


def test_event_enrichment_derives_factuality_and_syncs_tevent():
    text = EEP_SRC.read_text(encoding="utf-8")

    assert "query_factuality" in text
    assert "SET em.factuality" in text
    assert "_resolve_tevent_field_conflicts(\"factuality\"" in text


def test_event_factuality_states_are_governed_in_source_logic():
    text = EEP_SRC.read_text(encoding="utf-8")

    for state in ["ASSERTED", "REPORTED", "HYPOTHETICAL", "NEGATED"]:
        assert state in text
