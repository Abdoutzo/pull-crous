import os
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import config


PARIS = ZoneInfo("Europe/Paris")


class ConfigWindowTests(unittest.TestCase):
    def _dt(self, hour: int, minute: int) -> datetime:
        return datetime(2026, 5, 15, hour, minute, tzinfo=PARIS)

    def test_email_window_boundaries(self):
        self.assertFalse(config.is_within_email_window(self._dt(7, 59)))
        self.assertTrue(config.is_within_email_window(self._dt(8, 0)))
        self.assertTrue(config.is_within_email_window(self._dt(17, 59)))
        self.assertFalse(config.is_within_email_window(self._dt(18, 0)))

    def test_daily_summary_window_boundaries(self):
        self.assertFalse(config.is_daily_summary_window(self._dt(17, 54)))
        self.assertTrue(config.is_daily_summary_window(self._dt(17, 55)))
        self.assertTrue(config.is_daily_summary_window(self._dt(17, 59)))
        self.assertFalse(config.is_daily_summary_window(self._dt(18, 0)))

    def test_force_email_window_reads_env(self):
        with patch.dict(os.environ, {"FORCE_EMAIL_WINDOW": "true"}, clear=False):
            self.assertTrue(config.is_force_email_window())
        with patch.dict(os.environ, {"FORCE_EMAIL_WINDOW": "false"}, clear=False):
            self.assertFalse(config.is_force_email_window())


if __name__ == "__main__":
    unittest.main()
