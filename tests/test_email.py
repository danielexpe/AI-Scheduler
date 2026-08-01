import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEmailValidation(unittest.TestCase):

    def setUp(self):
        from importlib import reload
        import app.email_sender
        reload(app.email_sender)
        self.email_module = app.email_sender

    def test_valid_emails(self):
        valid = [
            "user@example.com",
            "a@b.co",
            "name.surname@domain.com.br",
            "name+tag@gmail.com",
            "user_name@sub.domain.org",
        ]
        for email in valid:
            self.assertTrue(self.email_module.is_valid_email(email), f"Should be valid: {email}")

    def test_invalid_emails(self):
        invalid = [
            "",
            "notanemail",
            "@domain.com",
            "user@",
            "user@.com",
            "user @domain.com",
            "user@domain",
            None,
        ]
        for email in invalid:
            if email is None:
                continue
            self.assertFalse(self.email_module.is_valid_email(email), f"Should be invalid: {email}")


class TestEmailWrapper(unittest.TestCase):

    def setUp(self):
        from importlib import reload
        import app.email_sender
        reload(app.email_sender)
        self.email_module = app.email_sender

    def test_wrapper_contains_expected_elements(self):
        self.assertIn("AI Mail Scheduler", self.email_module.EMAIL_WRAPPER)
        self.assertIn("{subject}", self.email_module.EMAIL_WRAPPER)
        self.assertIn("{date}", self.email_module.EMAIL_WRAPPER)
        self.assertIn("{body}", self.email_module.EMAIL_WRAPPER)
        self.assertIn("utf-8", self.email_module.EMAIL_WRAPPER.lower())


class TestEmailSending(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._saved_env = {}
        for key in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "SMTP_SERVER",
                     "SMTP_PORT", "EMAIL_FROM_NAME"):
            cls._saved_env[key] = os.environ.get(key)

    @classmethod
    def tearDownClass(cls):
        for key, orig_value in cls._saved_env.items():
            if orig_value is not None:
                os.environ[key] = orig_value
            elif key in os.environ:
                del os.environ[key]

    def setUp(self):
        os.environ.update({
            "GMAIL_USER": "test@gmail.com",
            "GMAIL_APP_PASSWORD": "test-app-password-16ch",
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "EMAIL_FROM_NAME": "Test Scheduler",
        })
        from importlib import reload
        import app.email_sender
        reload(app.email_sender)
        self.email_module = app.email_sender

    def tearDown(self):
        for key in self._saved_env:
            if self._saved_env[key] is not None:
                os.environ[key] = self._saved_env[key]
            elif key in os.environ:
                del os.environ[key]

    @patch("app.email_sender.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class):
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        success, error = self.email_module.send_email(
            "dest@example.com",
            "[Scheduler] Test Subject",
            "<p>Hello World</p>"
        )

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @patch("app.email_sender.smtplib.SMTP")
    def test_send_email_invalid_recipient(self, mock_smtp_class):
        success, error = self.email_module.send_email(
            "invalid-email",
            "Subject",
            "<p>Body</p>"
        )
        self.assertFalse(success)
        self.assertIn("inv", error.lower())

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials(self):
        from importlib import reload
        import app.email_sender
        reload(app.email_sender)

        success, error = app.email_sender.send_email(
            "dest@example.com",
            "Subject",
            "<p>Body</p>"
        )
        self.assertFalse(success)
        self.assertIn("configurado", error.lower())

    @patch("app.email_sender.smtplib.SMTP")
    def test_authentication_error(self, mock_smtp_class):
        import smtplib
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        success, error = self.email_module.send_email(
            "dest@example.com",
            "Subject",
            "<p>Body</p>"
        )
        self.assertFalse(success)
        self.assertIn("autentica", error.lower())

    @patch("app.email_sender.smtplib.SMTP")
    def test_recipient_refused(self, mock_smtp_class):
        import smtplib
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = smtplib.SMTPRecipientsRefused({"bad@x.com": (550, b"refused")})
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        success, error = self.email_module.send_email(
            "bad@x.com",
            "Subject",
            "<p>Body</p>"
        )
        self.assertFalse(success)
        self.assertIn("recusado", error.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
