from textgraphx.text_normalization import normalize_naf_raw_text


def test_preserve_mode_keeps_line_breaks():
    raw = "Title\n\nDate\n\nBody sentence."
    out = normalize_naf_raw_text(raw, mode="preserve")
    assert "\n\n" in out
    assert out == raw


def test_legacy_mode_strips_line_breaks():
    raw = "Title\n\nDate\n\nBody sentence."
    out = normalize_naf_raw_text(raw, mode="legacy")
    assert "\n" not in out
    assert "TitleDateBody" in out


def test_meantime_mode_inserts_sentence_boundary_on_blankline_blocks():
    raw = "Markets dragged down by credit crisis\n\nAugust 10, 2007\n\nGlobal stock markets fell today."
    out = normalize_naf_raw_text(raw, mode="meantime")
    assert out.startswith("Markets dragged down by credit crisis. August 10, 2007. Global stock markets fell today.")


def test_auto_mode_detects_meantime_style_header_blocks():
    raw = "Markets dragged down by credit crisis\n\nAugust 10, 2007\n\nGlobal stock markets fell today."
    out = normalize_naf_raw_text(raw, mode="auto")
    assert ". August 10, 2007." in out
