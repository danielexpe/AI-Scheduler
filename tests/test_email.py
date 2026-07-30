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

    @patch.dict(os.environ, {
        "GMAIL_USER": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test-app-password-16ch",
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "EMAIL_FROM_NAME": "Test Scheduler",
    })
    def setUp(self):
        from importlib import reload
        import app.email_sender
        reload(app.email_sender)
        self.email_module = app.email_sender

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
