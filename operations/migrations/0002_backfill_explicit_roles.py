from django.db import migrations


def backfill_explicit_roles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Patient = apps.get_model("patients", "Patient")
    Doctor = apps.get_model("doctors", "Doctor")
    RoleAssignment = apps.get_model("operations", "RoleAssignment")

    patient_user_ids = Patient.objects.values_list("user_id", flat=True)
    for user_id in patient_user_ids.iterator():
        RoleAssignment.objects.get_or_create(
            user_id=user_id,
            role="patient",
            facility_id=None,
            defaults={"is_active": True},
        )

    doctor_user_ids = Doctor.objects.values_list("user_id", flat=True)
    for user_id in doctor_user_ids.iterator():
        RoleAssignment.objects.get_or_create(
            user_id=user_id,
            role="doctor",
            facility_id=None,
            defaults={"is_active": True},
        )

    superuser_ids = User.objects.filter(is_superuser=True).values_list(
        "id",
        flat=True,
    )
    for user_id in superuser_ids.iterator():
        RoleAssignment.objects.get_or_create(
            user_id=user_id,
            role="administrator",
            facility_id=None,
            defaults={"is_active": True},
        )


def reverse_backfill(apps, schema_editor):
    RoleAssignment = apps.get_model("operations", "RoleAssignment")
    RoleAssignment.objects.filter(
        facility_id=None,
        role__in=["patient", "doctor", "administrator"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0001_initial"),
        ("patients", "0003_patient_profile_fields"),
        ("doctors", "0004_modernize_doctor_and_reviews"),
    ]

    operations = [
        migrations.RunPython(backfill_explicit_roles, reverse_backfill),
    ]
