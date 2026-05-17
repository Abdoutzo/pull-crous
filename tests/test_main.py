import os
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import main


PARIS = ZoneInfo("Europe/Paris")


class MainCheckTests(unittest.TestCase):
    def _dt(self, hour: int, minute: int) -> datetime:
        return datetime(2026, 5, 15, hour, minute, tzinfo=PARIS)

    def _state(self) -> dict:
        return {
            "seen_ids": set(),
            "daily_date": "2026-05-15",
            "daily_ids": set(),
            "daily_items": [],
            "last_summary_date": "",
        }

    def test_outside_email_window_skips_fetch(self):
        state_data = self._state()

        with patch.object(main, "current_local_time", return_value=self._dt(7, 30)), \
             patch.object(main, "is_force_email_window", return_value=False), \
             patch.object(main, "fetch_available_accommodations") as fetch_mock, \
             patch.object(main, "save_runtime_state") as save_mock:
            result = main.check([], state_data)

        fetch_mock.assert_not_called()
        save_mock.assert_called_once_with(state_data)
        self.assertIs(result, state_data)

    def test_force_email_window_raises_when_delivery_is_required(self):
        state_data = self._state()
        available = [{
            "id": "80",
            "label": "Test listing",
            "url": "https://example.test/80",
            "area": {},
            "occupationModes": [],
            "residence": {},
        }]

        with patch.dict(os.environ, {"REQUIRE_EMAIL_SUCCESS": "true"}, clear=False), \
             patch.object(main, "current_local_time", return_value=self._dt(21, 0)), \
             patch.object(main, "is_force_email_window", return_value=True), \
             patch.object(main, "fetch_available_accommodations", return_value=available), \
             patch.object(main, "send_alerts", return_value=False), \
             patch.object(main, "save_runtime_state") as save_mock:
            with self.assertRaisesRegex(RuntimeError, "Alert email delivery failed"):
                main.check([{"id": "80"}], state_data)

        save_mock.assert_not_called()

    def test_new_listing_success_updates_state(self):
        state_data = self._state()
        available = [{
            "id": "91",
            "label": "Choisy T1",
            "url": "https://example.test/91",
            "area": {"min": 20, "max": 26},
            "occupationModes": [],
            "residence": {"label": "CHOISY", "address": "120 avenue de Choisy 75013 Paris"},
        }]

        with patch.dict(os.environ, {"REQUIRE_EMAIL_SUCCESS": "false"}, clear=False), \
             patch.object(main, "current_local_time", return_value=self._dt(10, 0)), \
             patch.object(main, "is_force_email_window", return_value=False), \
             patch.object(main, "fetch_available_accommodations", return_value=available), \
             patch.object(main, "send_alerts", return_value=True), \
             patch.object(main, "save_runtime_state") as save_mock:
            result = main.check([{"id": "91"}], state_data)

        self.assertEqual(result["seen_ids"], {"91"})
        self.assertEqual(result["daily_ids"], {"91"})
        self.assertEqual(len(result["daily_items"]), 1)
        self.assertEqual(result["daily_items"][0]["id"], "91")
        save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
