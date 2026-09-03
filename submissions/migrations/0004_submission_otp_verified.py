from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0003_loan_application_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="otp_verified",
            field=models.BooleanField(default=False),
        ),
    ]
