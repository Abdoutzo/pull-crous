import unittest
from unittest.mock import MagicMock, patch

import notifier


class NotifierProviderTests(unittest.TestCase):
    def _item(self) -> dict:
        return {
            "id": "91",
            "label": "Choisy T1",
            "url": "https://example.test/91",
            "area": {"min": 20, "max": 26},
            "occupationModes": [],
            "residence": {"label": "CHOISY", "address": "120 avenue de Choisy 75013 Paris"},
        }

    def test_send_alerts_uses_resend_when_configured(self):
        response = MagicMock()
        response.is_success = True
        response.json.return_value = {"id": "email_123"}

        with patch.object(notifier, "EMAIL_PROVIDER", "auto"), \
             patch.object(notifier, "RESEND_API_KEY", "re_test"), \
             patch.object(notifier, "RESEND_FROM_EMAIL", "alerts@example.com"), \
             patch.object(notifier, "RESEND_REPLY_TO", "reply@example.com"), \
             patch.object(notifier, "RESEND_API_BASE_URL", "https://api.resend.com"), \
             patch.object(notifier, "load_recipients", return_value=["user@example.com"]), \
             patch.object(notifier.httpx, "post", return_value=response) as post_mock:
            result = notifier.send_alerts([self._item()])

        self.assertTrue(result)
        post_mock.assert_called_once()
        _, kwargs = post_mock.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer re_test")
        self.assertEqual(kwargs["headers"]["User-Agent"], "pull-crous/1.0")
        self.assertEqual(kwargs["json"]["from"], "CROUS Bot <alerts@example.com>")
        self.assertEqual(kwargs["json"]["to"], ["user@example.com"])
        self.assertEqual(kwargs["json"]["reply_to"], "reply@example.com")
        self.assertIn("CROUS alert", kwargs["json"]["subject"])
        self.assertIn("Choisy T1", kwargs["json"]["text"])
        self.assertIn("https://example.test/91", kwargs["json"]["html"])

    def test_send_alerts_returns_false_when_resend_config_is_missing(self):
        with patch.object(notifier, "EMAIL_PROVIDER", "resend"), \
             patch.object(notifier, "RESEND_API_KEY", None), \
             patch.object(notifier, "RESEND_FROM_EMAIL", None), \
             patch.object(notifier, "load_recipients", return_value=["user@example.com"]), \
             patch.object(notifier.httpx, "post") as post_mock:
            result = notifier.send_alerts([self._item()])

        self.assertFalse(result)
        post_mock.assert_not_called()

    def test_send_alerts_can_still_use_smtp_explicitly(self):
        smtp_client = MagicMock()
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp_client
        smtp_context.__exit__.return_value = False

        with patch.object(notifier, "EMAIL_PROVIDER", "smtp"), \
             patch.object(notifier, "SENDER_EMAIL", "sender@example.com"), \
             patch.object(notifier, "SMTP_HOST", "smtp.example.com"), \
             patch.object(notifier, "SMTP_PORT", 587), \
             patch.object(notifier, "SMTP_USERNAME", "sender@example.com"), \
             patch.object(notifier, "SMTP_PASSWORD", "secret"), \
             patch.object(notifier, "SMTP_SECURITY", "starttls"), \
             patch.object(notifier, "load_recipients", return_value=["user@example.com"]), \
             patch.object(notifier, "_open_smtp", return_value=smtp_context):
            result = notifier.send_alerts([])

        self.assertTrue(result)
        smtp_client.login.assert_called_once_with("sender@example.com", "secret")
        smtp_client.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
