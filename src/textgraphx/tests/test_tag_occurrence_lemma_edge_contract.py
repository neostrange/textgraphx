try:
    from textgraphx.text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor
except ModuleNotFoundError:
    from text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor

from pathlib import Path


class _DummyRepo:
    def execute_query_with_result_as_key(self, query, params):
        return {"query": query, "params": params}


def test_store_tag_query_uses_has_lemma_not_refers_to():
    executor = TagOccurrenceQueryExecutor(_DummyRepo())
    query = executor.get_tag_occurrence_query(store_tag=True)

    assert "[:HAS_LEMMA]" in query
    assert "[:REFERS_TO]" not in query


def test_text_processor_active_code_uses_has_lemma_not_refers_to_for_tag_links():
    src = Path(__file__).resolve().parents[1] / "pipeline" / "ingestion" / "text_processor.py"
    lines = src.read_text(encoding="utf-8").splitlines()
    active = [line for line in lines if not line.lstrip().startswith("#")]
    active_code = "\n".join(active)

    assert "[:HAS_LEMMA]" in active_code
    assert "(tag)<-[:REFERS_TO]-(tagOccurrence)" not in active_code
