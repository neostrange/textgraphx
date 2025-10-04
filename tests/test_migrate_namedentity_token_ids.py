import unittest

from textgraphx.tools import migrate_namedentity_token_ids as m


class FakeGraph:
    def __init__(self, tagocc_rows=None, ne_rows=None):
        # tagocc_rows: list of dicts returned by run for tagocc queries
        self.tagocc_rows = tagocc_rows or []
        self.ne_rows = ne_rows or []
        self.queries = []

    def run(self, query, params=None):
        # very small router: decide based on RETURN fields in query
        q = query.strip().upper()
        self.queries.append((q, params))
        class R:
            def __init__(self, rows):
                self._rows = rows

            def data(self):
                return self._rows

        if "MATCH (N:NAMEDENTITY) RETURN COUNT(N)" in q:
            return R([{"cnt": len(self.ne_rows)}])
        if "RETURN N.ID AS ID, N.INDEX AS START_INDEX" in q or "RETURN N.ID AS ID, N.INDEX AS START_INDEX, N.END_INDEX" in q:
            return R(self.ne_rows)
        # tagocc queries
        if "MATCH (T:TAGOCCURRENCE)" in q:
            # heuristically return provided tagocc rows (simulating different queries)
            return R(self.tagocc_rows)
        # default empty
        return R([])


class TestMigrateHelpers(unittest.TestCase):
    def test_compute_mappings_no_tag_matches(self):
        # no TagOccurrence rows -> mapping should be skipped
        fakeG = FakeGraph(tagocc_rows=[], ne_rows=[{"id": "1_10_15_PERSON", "start_index": 10, "end_index": 15, "type": "PERSON"}])
        nes = m.collect_namedentities(fakeG, batch=10)
        mappings, skipped = m.compute_mappings(fakeG, nes)
        self.assertEqual(len(mappings), 0)
        self.assertEqual(len(skipped), 1)

    def test_compute_mappings_with_tag_matches(self):
        # simulate tagocc rows that provide tok_index_doc for start and end
        tagrows = [{"tok_start": 5, "tok_end": 7}, {"tok_start": 5, "tok_end": 7}]
        # The FakeGraph.run will return tagrows for TagOccurrence queries; we craft ne_rows accordingly
        fakeG = FakeGraph(tagocc_rows=tagrows, ne_rows=[{"id": "1_100_110_MONEY", "start_index": 100, "end_index": 110, "type": "MONEY"}])
        nes = m.collect_namedentities(fakeG, batch=10)
        # monkeypatch find_tok_indices_for_ne to avoid running real subqueries
        original_finder = m.find_tok_indices_for_ne
        m.find_tok_indices_for_ne = lambda G, ne_id, s, e: (5, 7)
        try:
            mappings, skipped = m.compute_mappings(fakeG, nes)
            self.assertEqual(len(mappings), 1)
            self.assertEqual(mappings[0]["token_id"], "1_5_7_MONEY")
        finally:
            m.find_tok_indices_for_ne = original_finder

    def test_apply_mappings_calls_run(self):
        fakeG = FakeGraph()
        mappings = [{"ne_id": "1_100_110_MONEY", "token_id": "1_5_7_MONEY", "tok_start": 5, "tok_end": 7}]
        applied, errors = m.apply_mappings(fakeG, mappings, batch=10)
        # our FakeGraph returns empty data for the MATCH/SET query so applied should be 0
        self.assertEqual(applied, 0)
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
