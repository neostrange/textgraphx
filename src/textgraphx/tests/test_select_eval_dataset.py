import json

import pytest

from textgraphx.tools import select_eval_dataset


@pytest.mark.unit
def test_select_eval_dataset_materializes_matching_files(tmp_path):
    annotated = tmp_path / "annotated"
    original = tmp_path / "original"
    target = tmp_path / "selected"
    annotated.mkdir()
    original.mkdir()

    (annotated / "doc_a.xml").write_text("<Document/>", encoding="utf-8")
    (annotated / "doc_b.xml").write_text("<Document/>", encoding="utf-8")
    (original / "doc_a.naf").write_text("naf-a", encoding="utf-8")
    (original / "doc_b.naf").write_text("naf-b", encoding="utf-8")

    rc = select_eval_dataset.main.__wrapped__ if hasattr(select_eval_dataset.main, "__wrapped__") else None
    assert rc is None

    # Run through CLI surface for realistic behavior.
    argv = [
        "--annotated-dir",
        str(annotated),
        "--original-dir",
        str(original),
        "--target-dir",
        str(target),
        "--mode",
        "copy",
        "--clean",
    ]

    # Patch parser input by temporarily replacing sys.argv semantics.
    import sys

    old_argv = sys.argv
    try:
        sys.argv = ["select_eval_dataset"] + argv
        exit_code = select_eval_dataset.main()
    finally:
        sys.argv = old_argv

    assert exit_code == 0
    assert (target / "doc_a.naf").exists()
    assert (target / "doc_b.naf").exists()

    manifest = json.loads((target / "selection_manifest.json").read_text(encoding="utf-8"))
    assert manifest["annotated_docs"] == 2
    assert manifest["selected_docs"] == 2
    assert manifest["missing_docs"] == 0


@pytest.mark.unit
def test_select_eval_dataset_fail_on_missing_returns_nonzero(tmp_path):
    annotated = tmp_path / "annotated"
    original = tmp_path / "original"
    target = tmp_path / "selected"
    annotated.mkdir()
    original.mkdir()

    (annotated / "doc_a.xml").write_text("<Document/>", encoding="utf-8")
    (annotated / "doc_b.xml").write_text("<Document/>", encoding="utf-8")
    (original / "doc_a.naf").write_text("naf-a", encoding="utf-8")

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "select_eval_dataset",
            "--annotated-dir",
            str(annotated),
            "--original-dir",
            str(original),
            "--target-dir",
            str(target),
            "--fail-on-missing",
        ]
        exit_code = select_eval_dataset.main()
    finally:
        sys.argv = old_argv

    assert exit_code == 2
