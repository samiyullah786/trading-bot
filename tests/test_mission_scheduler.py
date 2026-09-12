from __future__ import annotations

import unittest

from src.mission_scheduler import MissionScheduler


class MissionSchedulerTests(unittest.TestCase):
    def test_selects_ready_action_and_respects_dependencies(self):
        actions = [
            {"action_id": "a", "depends_on": [], "verified": False},
            {"action_id": "b", "depends_on": ["a"], "verified": False},
        ]
        scheduler = MissionScheduler(actions)
        self.assertEqual(scheduler.next_ready().ready_index, 0)
        actions[0]["verified"] = True
        self.assertEqual(scheduler.next_ready().ready_index, 1)

    def test_rejects_missing_dependency(self):
        with self.assertRaisesRegex(ValueError, "MISSING_DEPENDENCY"):
            MissionScheduler([{"action_id": "a", "depends_on": ["missing"]}])

    def test_rejects_dependency_cycle(self):
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_CYCLE"):
            MissionScheduler([
                {"action_id": "a", "depends_on": ["b"]},
                {"action_id": "b", "depends_on": ["a"]},
            ])

    def test_rejects_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ACTION_ID"):
            MissionScheduler([{"action_id": "a"}, {"action_id": "a"}])

    def test_reports_complete(self):
        actions = [{"action_id": "a", "depends_on": [], "verified": True}]
        self.assertEqual(MissionScheduler(actions).next_ready().error, "COMPLETE")


if __name__ == "__main__":
    unittest.main()
