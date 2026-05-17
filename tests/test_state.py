import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import state


class StatePersistenceTests(unittest.TestCase):
    def test_save_runtime_state_creates_parent_dir_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "nested" / "seen_ids.json"
            payload = {
                "seen_ids": {"42", "17"},
                "daily_date": "2026-05-15",
                "daily_ids": {"42"},
                "daily_items": [{"id": "42", "label": "Test room"}],
                "last_summary_date": "2026-05-15",
            }

            with patch.object(state, "STATE_FILE", str(state_path)):
                state.save_runtime_state(payload)
                self.assertTrue(state_path.exists())

                loaded = state.load_runtime_state()
                self.assertEqual(loaded["seen_ids"], {"17", "42"})
                self.assertEqual(loaded["daily_ids"], {"42"})
                self.assertEqual(loaded["daily_date"], "2026-05-15")
                self.assertEqual(loaded["daily_items"], [{"id": "42", "label": "Test room"}])
                self.assertEqual(loaded["last_summary_date"], "2026-05-15")

    def test_load_runtime_state_supports_legacy_list_format(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "seen_ids.json"
            state_path.write_text(json.dumps([1, "2", None]), encoding="utf-8")

            with patch.object(state, "STATE_FILE", str(state_path)):
                loaded = state.load_runtime_state()
                self.assertEqual(loaded["seen_ids"], {"1", "2"})
                self.assertEqual(loaded["daily_ids"], set())
                self.assertEqual(loaded["daily_items"], [])


if __name__ == "__main__":
    unittest.main()
