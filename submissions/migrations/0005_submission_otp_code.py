from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0004_submission_otp_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="otp_code",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
    ]
