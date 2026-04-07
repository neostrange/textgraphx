import unittest

from textgraphx.tools import migrate_participation_edges as m


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows


class FakeGraph:
    def __init__(self, responses):
        self.responses = list(responses)
        self.queries = []

    def run(self, query, params=None):
        self.queries.append((query, params))
        if not self.responses:
            return _Rows([])
        return _Rows(self.responses.pop(0))


class TestParticipationEdgeMigration(unittest.TestCase):
    def test_backfill_in_frame_stops_on_zero_batch(self):
        # First batch creates 3, second creates 0 -> stop
        g = FakeGraph([
            [{"created": 3}],
            [{"created": 0}],
        ])
        total = m.backfill_in_frame(g, batch_size=100)
        self.assertEqual(total, 3)
        self.assertEqual(len(g.queries), 2)

    def test_backfill_in_mention_stops_on_zero_batch(self):
        g = FakeGraph([
            [{"created": 2}],
            [{"created": 1}],
            [{"created": 0}],
        ])
        total = m.backfill_in_mention(g, batch_size=50)
        self.assertEqual(total, 3)
        self.assertEqual(len(g.queries), 3)

    def test_run_migration_dry_run_collects_counts_without_writes(self):
        # Query sequence in run_migration(dry-run):
        # frame_candidates, mention_candidates, frame_missing_before,
        # mention_missing_before, frame_missing_after, mention_missing_after
        g = FakeGraph([
            [{"cnt": 10}],
            [{"cnt": 20}],
            [{"cnt": 4}],
            [{"cnt": 6}],
            [{"cnt": 4}],
            [{"cnt": 6}],
        ])
        out = m.run_migration(g, apply=False, batch_size=1000)
        self.assertEqual(out["frame_candidates"], 10)
        self.assertEqual(out["mention_candidates"], 20)
        self.assertEqual(out["created_in_frame"], 0)
        self.assertEqual(out["created_in_mention"], 0)
        self.assertEqual(out["frame_missing_before"], out["frame_missing_after"])
        self.assertEqual(out["mention_missing_before"], out["mention_missing_after"])

    def test_run_migration_apply_runs_backfills_and_recounts(self):
        # Sequence:
        # counts before (4), frame batches (2 then 0), mention batches (3 then 0), counts after (2)
        g = FakeGraph([
            [{"cnt": 100}],  # frame candidates
            [{"cnt": 120}],  # mention candidates
            [{"cnt": 5}],    # frame missing before
            [{"cnt": 7}],    # mention missing before
            [{"created": 2}],
            [{"created": 0}],
            [{"created": 3}],
            [{"created": 0}],
            [{"cnt": 3}],    # frame missing after
            [{"cnt": 4}],    # mention missing after
        ])
        out = m.run_migration(g, apply=True, batch_size=500)
        self.assertEqual(out["created_in_frame"], 2)
        self.assertEqual(out["created_in_mention"], 3)
        self.assertEqual(out["frame_missing_after"], 3)
        self.assertEqual(out["mention_missing_after"], 4)


if __name__ == "__main__":
    unittest.main()
