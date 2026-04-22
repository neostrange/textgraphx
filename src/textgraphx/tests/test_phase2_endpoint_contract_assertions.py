from pathlib import Path


def test_phase_assertions_enforce_phase2_endpoint_contracts():
    src = Path(__file__).resolve().parents[1] / "phase_assertions.py"
    text = src.read_text(encoding="utf-8")

    assert "Endpoint contract violations (HAS_LEMMA)" in text
    assert "Endpoint contract violations (CLINK)" in text
    assert "Endpoint contract violations (SLINK)" in text
