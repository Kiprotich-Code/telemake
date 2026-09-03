import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Submission",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(max_length=50)),
                (
                    "email",
                    models.EmailField(blank=True, default="", max_length=254),
                ),
                ("message", models.TextField()),
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("n8n_notified", models.BooleanField(default=False)),
                (
                    "n8n_notified_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "n8n_notification_error",
                    models.TextField(blank=True, default=""),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
