from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from doctors.models import Doctor
from patients.models import Patient

from .models import RoleAssignment


def ensure_role(user, role):
    RoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        facility=None,
        defaults={"is_active": True},
    )


@receiver(post_save, sender=Patient)
def assign_patient_role(sender, instance, **kwargs):
    ensure_role(instance.user, RoleAssignment.Role.PATIENT)


@receiver(post_save, sender=Doctor)
def assign_doctor_role(sender, instance, **kwargs):
    ensure_role(instance.user, RoleAssignment.Role.DOCTOR)


@receiver(post_save, sender=get_user_model())
def assign_superuser_role(sender, instance, **kwargs):
    if instance.is_superuser:
        ensure_role(instance, RoleAssignment.Role.ADMINISTRATOR)
