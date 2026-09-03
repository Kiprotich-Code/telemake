"""
Comprehensive test suite for the submissions app.

Covers:
  1. Form validation (SubmissionFormTests)
  2. View behaviour (SubmitViewTests)
  3. DB persistence (SubmissionModelTests)
  4. n8n service layer (NotifyN8nTests)
  5. Security (SecurityTests)
"""

import string
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .forms import SubmissionForm
from .models import Submission
from .services import notify_n8n

# ---------------------------------------------------------------------------
# Shared settings override — suppresses _require_env() errors and avoids
# accidental outbound HTTP calls during tests.
# ---------------------------------------------------------------------------
TEST_SETTINGS = dict(
    N8N_WEBHOOK_URL="https://test.example.com/webhook",
    N8N_WEBHOOK_SECRET="test-secret-123",
)

_VALID_FORM_DATA = {
    "name": "Alice Smith",
    "phone": "0712345678",
    "email": "alice@example.com",
    "message": "Hello there",
}


# ===========================================================================
# 1. Form validation tests
# ===========================================================================

class SubmissionFormTests(SimpleTestCase):
    """Unit-tests for SubmissionForm validation — no DB required."""

    def test_valid_form(self):
        """All fields filled including email → form is valid."""
        form = SubmissionForm(data=_VALID_FORM_DATA)
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_without_email(self):
        """Email omitted → form is still valid (email is optional)."""
        data = {**_VALID_FORM_DATA, "email": ""}
        form = SubmissionForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name(self):
        """Blank name → form is invalid with an error on the name field."""
        data = {**_VALID_FORM_DATA, "name": ""}
        form = SubmissionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_phone(self):
        """Blank phone → form is invalid with an error on the phone field."""
        data = {**_VALID_FORM_DATA, "phone": ""}
        form = SubmissionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_missing_message(self):
        """Blank message → form is invalid with an error on the message field."""
        data = {**_VALID_FORM_DATA, "message": ""}
        form = SubmissionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_invalid_email(self):
        """'not-an-email' as email → form invalid, email field has error."""
        data = {**_VALID_FORM_DATA, "email": "not-an-email"}
        form = SubmissionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_whitespace_name(self):
        """Whitespace-only name → form invalid (Django strips via clean)."""
        data = {**_VALID_FORM_DATA, "name": "   "}
        form = SubmissionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


# ===========================================================================
# 2. View tests
# ===========================================================================

@override_settings(**TEST_SETTINGS)
class SubmitViewTests(TestCase):
    """Integration tests for the submit and success views."""

    def setUp(self):
        self.submit_url = reverse("submissions:submit")
        self.success_url = reverse("submissions:success")

    def test_get_submit_page(self):
        """GET /submit/ returns HTTP 200."""
        response = self.client.get(self.submit_url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_redirects(self):
        """Valid POST → 302 redirect to /success/."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            response = self.client.post(self.submit_url, data=_VALID_FORM_DATA)
        self.assertRedirects(response, self.success_url)

    def test_post_valid_saves_to_db(self):
        """Valid POST creates exactly one Submission record."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            self.client.post(self.submit_url, data=_VALID_FORM_DATA)
        self.assertEqual(Submission.objects.count(), 1)

    def test_post_invalid_rerenders(self):
        """POST with missing name → 200 re-render, form errors present."""
        data = {**_VALID_FORM_DATA, "name": ""}
        response = self.client.post(self.submit_url, data=data)
        self.assertEqual(response.status_code, 200)
        # Form should be in context with errors
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_success_page(self):
        """GET /success/ returns HTTP 200."""
        response = self.client.get(self.success_url)
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 3. DB persistence tests
# ===========================================================================

class SubmissionModelTests(TestCase):
    """Tests for Submission model field storage and defaults."""

    def _make_submission(self, **overrides):
        defaults = {
            "name": "Bob Jones",
            "phone": "0700000001",
            "email": "bob@example.com",
            "message": "Test message",
        }
        defaults.update(overrides)
        return Submission.objects.create(**defaults)

    def test_submission_saved_correctly(self):
        """All fields are persisted correctly to the database."""
        sub = self._make_submission()
        fetched = Submission.objects.get(pk=sub.pk)

        self.assertEqual(fetched.name, "Bob Jones")
        self.assertEqual(fetched.phone, "0700000001")
        self.assertEqual(fetched.email, "bob@example.com")
        self.assertEqual(fetched.message, "Test message")
        self.assertIsNotNone(fetched.created_at)

    def test_default_n8n_fields(self):
        """New Submission has n8n_notified=False and n8n_notification_error=''."""
        sub = self._make_submission()
        self.assertFalse(sub.n8n_notified)
        self.assertEqual(sub.n8n_notification_error, "")
        self.assertIsNone(sub.n8n_notified_at)


# ===========================================================================
# 4. n8n service tests
# ===========================================================================

@override_settings(**TEST_SETTINGS)
class NotifyN8nTests(TestCase):
    """Tests for the notify_n8n() service function."""

    def setUp(self):
        self.submission = Submission.objects.create(
            name="Carol White",
            phone="0722222222",
            email="carol@example.com",
            message="Service layer test",
        )

    # --- Payload shape -------------------------------------------------------

    def test_payload_shape(self):
        """notify_n8n posts JSON with expected top-level keys and nested data."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            notify_n8n(self.submission)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]

        # Top-level keys
        self.assertIn("event", payload)
        self.assertIn("submission_id", payload)
        self.assertIn("data", payload)
        self.assertIn("created_at", payload)

        # Event value
        self.assertEqual(payload["event"], "submission.created")

        # Nested data keys
        data = payload["data"]
        self.assertIn("name", data)
        self.assertIn("phone", data)
        self.assertIn("email", data)
        self.assertIn("message", data)

    def test_created_at_is_iso8601_utc(self):
        """created_at in the payload is a valid ISO 8601 UTC string."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            notify_n8n(self.submission)

        _, kwargs = mock_post.call_args
        created_at = kwargs["json"]["created_at"]

        # Must parse without error
        parsed = datetime.fromisoformat(created_at)
        # Must carry UTC offset
        self.assertIsNotNone(parsed.tzinfo)
        # Offset must be +00:00 (UTC)
        self.assertIn(created_at[-6:], ("+00:00",))

    # --- Header --------------------------------------------------------------

    def test_webhook_secret_header(self):
        """X-Webhook-Secret header equals settings.N8N_WEBHOOK_SECRET."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            notify_n8n(self.submission)

        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        self.assertEqual(headers["X-Webhook-Secret"], "test-secret-123")

    # --- 2xx success path ----------------------------------------------------

    def test_success_updates_notified_true(self):
        """200 response → n8n_notified=True and n8n_notified_at is set."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            notify_n8n(self.submission)

        self.submission.refresh_from_db()
        self.assertTrue(self.submission.n8n_notified)
        self.assertIsNotNone(self.submission.n8n_notified_at)

    def test_success_clears_error_field(self):
        """200 response → n8n_notification_error is cleared to ''."""
        # Pre-populate an error to confirm it gets wiped
        self.submission.n8n_notification_error = "old error"
        self.submission.save(update_fields=["n8n_notification_error"])

        with patch("submissions.services.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            notify_n8n(self.submission)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.n8n_notification_error, "")

    # --- Timeout path --------------------------------------------------------

    def test_timeout_submission_survives(self):
        """Timeout → submission record still exists in DB."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            notify_n8n(self.submission)

        self.assertTrue(Submission.objects.filter(pk=self.submission.pk).exists())

    def test_timeout_sets_notified_false(self):
        """Timeout → n8n_notified=False, n8n_notification_error='Request timed out'."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            notify_n8n(self.submission)

        self.submission.refresh_from_db()
        self.assertFalse(self.submission.n8n_notified)
        self.assertEqual(self.submission.n8n_notification_error, "Request timed out")

    # --- HTTP 500 path -------------------------------------------------------

    def test_http_500_submission_survives(self):
        """HTTP 500 → submission record still exists in DB."""
        mock_response = MagicMock(ok=False, status_code=500)
        with patch("submissions.services.requests.post", return_value=mock_response):
            notify_n8n(self.submission)

        self.assertTrue(Submission.objects.filter(pk=self.submission.pk).exists())

    def test_http_500_sets_notified_false(self):
        """HTTP 500 → n8n_notified=False, n8n_notification_error contains '500'."""
        mock_response = MagicMock(ok=False, status_code=500)
        with patch("submissions.services.requests.post", return_value=mock_response):
            notify_n8n(self.submission)

        self.submission.refresh_from_db()
        self.assertFalse(self.submission.n8n_notified)
        self.assertIn("500", self.submission.n8n_notification_error)

    # --- ConnectionError path ------------------------------------------------

    def test_connection_error_handled(self):
        """ConnectionError → no exception propagates, n8n_notified=False."""
        with patch("submissions.services.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("refused")
            # Must not raise
            try:
                notify_n8n(self.submission)
            except Exception as exc:
                self.fail(f"notify_n8n raised an unexpected exception: {exc}")

        self.submission.refresh_from_db()
        self.assertFalse(self.submission.n8n_notified)


# ===========================================================================
# 5. Security tests
# ===========================================================================

@override_settings(**TEST_SETTINGS)
class SecurityTests(TestCase):
    """Ensure sensitive values never leak into rendered HTML."""

    def test_secret_not_in_form_html(self):
        """GET /submit/ response body must NOT contain the webhook secret value."""
        url = reverse("submissions:submit")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertNotIn("test-secret-123", content)
