from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0002_alter_submission_id_alter_submission_n8n_notified_at"),
    ]

    operations = [
        # Add new fields with safe one-off defaults for any existing rows
        migrations.AddField(
            model_name="submission",
            name="first_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="last_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="age",
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="employment_status",
            field=models.CharField(
                choices=[
                    ("employed", "Employed"),
                    ("self_employed", "Self-Employed"),
                    ("unemployed", "Unemployed"),
                    ("student", "Student"),
                    ("retired", "Retired"),
                ],
                default="employed",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="submission",
            name="pin",
            field=models.CharField(default="", max_length=10),
            preserve_default=False,
        ),
        # Make legacy fields explicitly blank/default so they stay optional
        migrations.AlterField(
            model_name="submission",
            name="message",
            field=models.TextField(blank=True, default=""),
        ),
    ]
