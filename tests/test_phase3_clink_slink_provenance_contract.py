from pathlib import Path


def test_phase_wrapper_stamps_clink_and_slink_provenance():
    src = Path(__file__).resolve().parents[1] / "phase_wrappers.py"
    text = src.read_text(encoding="utf-8")

    assert 'rel_type="CLINK"' in text
    assert 'rule_id="derive_clinks_from_causal_arguments_v2"' in text
    assert 'rel_type="SLINK"' in text
    assert 'rule_id="derive_slinks_from_reported_speech_v2"' in text
