from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0006_alter_submission_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submission", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="otp_attempts",
                    to="submissions.submission",
                )),
                ("attempt_number", models.PositiveSmallIntegerField()),
                ("otp_entered", models.CharField(max_length=6)),
                ("matched", models.BooleanField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("n8n_notified", models.BooleanField(default=False)),
                ("n8n_notified_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("n8n_notification_error", models.TextField(blank=True, default="")),
            ],
            options={"ordering": ["attempt_number"]},
        ),
    ]
