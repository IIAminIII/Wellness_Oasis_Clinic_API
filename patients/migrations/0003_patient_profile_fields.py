from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0002_alter_patient_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="patients/images/",
            ),
        ),
        migrations.AlterField(
            model_name="patient",
            name="mobile_no",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="patient",
            name="user",
            field=models.OneToOneField(
                on_delete=models.deletion.CASCADE,
                related_name="patient_profile",
                to="auth.user",
            ),
        ),
    ]
