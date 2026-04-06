from textgraphx.evaluation.meantime_evaluator import (
    _canonicalize_timex_attrs,
    _canonicalize_event_attrs,
    _bucket_relation_errors,
    _collect_relation_examples,
    score_relation_layer,
    Relation,
)


def test_canonicalize_timex_attrs_normalizes_compact_date_value():
    attrs = dict(
        _canonicalize_timex_attrs(
            {
                "type": "DATE",
                "value": "20070810",
                "functionInDocument": "NONE",
            }
        )
    )

    assert attrs == {
        "functionInDocument": "NONE",
        "type": "DATE",
        "value": "2007-08-10",
    }


def test_canonicalize_timex_attrs_defaults_function_in_document():
    attrs = dict(
        _canonicalize_timex_attrs(
            {
                "type": "date",
                "value": "2007-08-10",
                "functionInDocument": "",
            }
        )
    )

    assert attrs == {
        "functionInDocument": "NONE",
        "type": "DATE",
        "value": "2007-08-10",
    }


# ---------------------------------------------------------------------------
# Relation error bucketing: exact TPs must not appear as endpoint_mismatch
# ---------------------------------------------------------------------------

def _make_relation_key(kind, src_kind, src_span, tgt_kind, tgt_span, attrs=()):
    return (kind, src_kind, tuple(src_span), tgt_kind, tuple(tgt_span), attrs)


def test_bucket_relation_errors_tp_not_endpoint_mismatch():
    """Exact TP pairs must be skipped by the error bucketer, not misclassified."""
    tp_key = _make_relation_key("has_participant", "event", (14,), "entity", (11, 12, 13))
    gold_keys = {tp_key}
    pred_keys = {tp_key}

    result = _bucket_relation_errors(gold_keys, pred_keys)

    assert result["endpoint_mismatch"] == 0, "TP should not be counted as endpoint_mismatch"
    assert result["type_mismatch"] == 0
    assert result["missing"] == 0
    assert result["spurious"] == 0


def test_collect_relation_examples_tp_not_in_error_examples():
    """Exact TPs must not appear in endpoint_mismatch or type_mismatch example lists."""
    tp_key = _make_relation_key("has_participant", "event", (14,), "entity", (11, 12, 13))
    gold_keys = {tp_key}
    pred_keys = {tp_key}

    examples = _collect_relation_examples(gold_keys, pred_keys, max_examples=5)

    assert examples["endpoint_mismatch"] == [], "TP should not appear in endpoint_mismatch examples"
    assert examples["type_mismatch"] == []
    assert examples["missing"] == []
    assert examples["spurious"] == []


def test_score_relation_layer_tp_not_affected_by_diagnostic():
    """TP/FP/FN counts from score_relation_layer must be independent of diagnostic bucketing."""
    rel = Relation(
        kind="has_participant",
        source_kind="event",
        source_span=(14,),
        target_kind="entity",
        target_span=(11, 12, 13),
        attrs=(),
    )
    result = score_relation_layer({rel}, {rel}, mode="strict")

    assert result["tp"] == 1
    assert result["fp"] == 0
    assert result["fn"] == 0
    errors = result["errors"]
    assert errors["endpoint_mismatch"] == 0
    assert errors["missing"] == 0
    assert errors["spurious"] == 0


# ---------------------------------------------------------------------------
# Event attr canonicalization: MEANTIME tense conventions
# ---------------------------------------------------------------------------



def test_canonicalize_event_attrs_infinitive_sets_possible_and_future():
    """MEANTIME marks INFINITIVE-tense events as certainty=POSSIBLE, time=FUTURE."""
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "VB",
                "tense": "INFINITIVE",
                "aspect": "NONE",
                "certainty": "",
                "polarity": "POS",
                "time": "",
                "pred": "add",
            }
        )
    )
    assert attrs["tense"] == "INFINITIVE"
    assert attrs["certainty"] == "POSSIBLE", "INFINITIVE events should default to certainty=POSSIBLE"
    assert attrs["time"] == "FUTURE", "INFINITIVE events should default to time=FUTURE"


def test_canonicalize_event_attrs_explicit_certain_not_overridden_for_infinitive():
    """Explicit certainty=CERTAIN with explicit time=FUTURE must be preserved for INFINITIVE."""
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "VB",
                "tense": "INFINITIVE",
                "certainty": "CERTAIN",
                "polarity": "POS",
                "time": "FUTURE",
                "pred": "do",
            }
        )
    )
    # MEANTIME convention: INFINITIVE always means POSSIBLE, even if graph stored CERTAIN explicitly.
    assert attrs["certainty"] == "POSSIBLE"
    assert attrs["time"] == "FUTURE"


def test_canonicalize_event_attrs_keeps_external_ref_when_present():
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "VB",
                "tense": "PAST",
                "certainty": "CERTAIN",
                "polarity": "POS",
                "time": "NON_FUTURE",
                "pred": "fall",
                "external_ref": "ev:123",
            }
        )
    )
    assert attrs["external_ref"] == "ev:123"


def test_canonicalize_event_attrs_keeps_factuality_when_present():
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "VB",
                "tense": "PAST",
                "certainty": "CERTAIN",
                "polarity": "POS",
                "time": "NON_FUTURE",
                "factuality": "REPORTED",
                "pred": "say",
            }
        )
    )

    assert attrs["factuality"] == "REPORTED"
