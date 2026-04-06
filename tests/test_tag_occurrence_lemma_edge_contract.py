try:
    from textgraphx.text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor
except ModuleNotFoundError:
    from text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor


class _DummyRepo:
    def execute_query_with_result_as_key(self, query, params):
        return {"query": query, "params": params}


def test_store_tag_query_uses_has_lemma_not_refers_to():
    executor = TagOccurrenceQueryExecutor(_DummyRepo())
    query = executor.get_tag_occurrence_query(store_tag=True)

    assert "[:HAS_LEMMA]" in query
    assert "[:REFERS_TO]" not in query
