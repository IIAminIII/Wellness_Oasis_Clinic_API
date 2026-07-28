import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0002_alter_appointment_time"),
        ("doctors", "0004_modernize_doctor_and_reviews"),
    ]

    operations = [
        migrations.RenameField(
            model_name="appointment",
            old_name="appointment_types",
            new_name="appointment_type",
        ),
        migrations.AlterField(
            model_name="appointment",
            name="appointment_status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Confirmed", "Confirmed"),
                    ("Running", "Running"),
                    ("Completed", "Completed"),
                    ("Cancelled", "Cancelled"),
                ],
                default="Pending",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="appointment_type",
            field=models.CharField(
                choices=[("Offline", "In person"), ("Online", "Online")],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="symptoms",
            field=models.TextField(max_length=2000),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="patient",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="appointments",
                to="patients.patient",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="doctor",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="appointments",
                to="doctors.doctor",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="time",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="appointments",
                to="doctors.availabletime",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="scheduled_date",
            field=models.DateField(default=datetime.date.today),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="appointment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["doctor", "scheduled_date", "time"],
                name="appt_doctor_slot_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["patient", "scheduled_date"],
                name="appt_patient_date_idx",
            ),
        ),
        migrations.AlterModelOptions(
            name="appointment",
            options={"ordering": ["-scheduled_date", "-created_at"]},
        ),
    ]
