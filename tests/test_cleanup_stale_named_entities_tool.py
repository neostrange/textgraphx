from textgraphx.tools import cleanup_stale_named_entities as tool


def test_build_scope_filters_includes_requested_constraints():
    where, params = tool.build_scope_filters(document_id="42", stale_run_id="run-1", older_than_ms=1000)

    assert "ne.stale = true" in where
    assert "coalesce(ne.token_id, ne.id) STARTS WITH $doc_prefix" in where
    assert "ne.stale_run_id = $stale_run_id" in where
    assert "ne.stale_at <= timestamp() - $older_than_ms" in where
    assert params["doc_prefix"] == "42_"
    assert params["stale_run_id"] == "run-1"
    assert params["older_than_ms"] == 1000


def test_run_cleanup_dry_run_reports_current_inventory(monkeypatch):
    monkeypatch.setattr(tool, "_count_stale_nodes", lambda *args, **kwargs: 7)
    monkeypatch.setattr(tool, "_count_stale_mention_edges", lambda *args, **kwargs: 3)
    monkeypatch.setattr(tool, "_count_stale_refers_to_edges", lambda *args, **kwargs: 2)

    result = tool.run_cleanup(
        graph=object(),
        apply=False,
        detach_delete=False,
        batch_size=100,
        max_iterations=10,
    )

    assert result["stale_nodes_before"] == 7
    assert result["mention_edges_before"] == 3
    assert result["refers_to_edges_before"] == 2
    assert result["retired_mention_edges"] == 0
    assert result["retired_refers_to_edges"] == 0
    assert result["deleted_stale_nodes"] == 0
    assert result["stale_nodes_after"] == 7


def test_run_cleanup_apply_retires_edges_and_deletes_nodes(monkeypatch):
    monkeypatch.setattr(tool, "_count_stale_nodes", lambda *args, **kwargs: 0)
    monkeypatch.setattr(tool, "_count_stale_mention_edges", lambda *args, **kwargs: 0)
    monkeypatch.setattr(tool, "_count_stale_refers_to_edges", lambda *args, **kwargs: 0)

    mention_batches = iter([4, 1, 0])
    refers_batches = iter([2, 0])
    node_batches = iter([3, 0])

    monkeypatch.setattr(
        tool,
        "_delete_mention_edges_batch",
        lambda *args, **kwargs: next(mention_batches),
    )
    monkeypatch.setattr(
        tool,
        "_delete_refers_to_edges_batch",
        lambda *args, **kwargs: next(refers_batches),
    )
    monkeypatch.setattr(
        tool,
        "_detach_delete_stale_nodes_batch",
        lambda *args, **kwargs: next(node_batches),
    )

    result = tool.run_cleanup(
        graph=object(),
        apply=True,
        detach_delete=True,
        batch_size=100,
        max_iterations=10,
    )

    assert result["retired_mention_edges"] == 5
    assert result["retired_refers_to_edges"] == 2
    assert result["deleted_stale_nodes"] == 3
