from django.conf import settings
from django.db import models

from doctors.models import AvailableTime, Doctor
from operations.models import Department, Facility
from patients.models import Patient


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        CONFIRMED = "Confirmed", "Confirmed"
        RUNNING = "Running", "Running"
        COMPLETED = "Completed", "Completed"
        CANCELLED = "Cancelled", "Cancelled"

    class Type(models.TextChoices):
        OFFLINE = "Offline", "In person"
        ONLINE = "Online", "Online"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    appointment_type = models.CharField(max_length=10, choices=Type.choices)
    appointment_status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    symptoms = models.TextField(max_length=2000)
    scheduled_date = models.DateField()
    time = models.ForeignKey(
        AvailableTime,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="appointments",
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="appointments",
        blank=True,
        null=True,
    )
    cancel = models.BooleanField(default=False)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="appointment_status_changes",
        blank=True,
        null=True,
    )
    status_changed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.scheduled_date} {self.time}: "
            f"{self.patient} with {self.doctor}"
        )

    class Meta:
        ordering = ["-scheduled_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["doctor", "scheduled_date", "time"],
                name="appt_doctor_slot_idx",
            ),
            models.Index(
                fields=["patient", "scheduled_date"],
                name="appt_patient_date_idx",
            ),
            models.Index(
                fields=["facility", "scheduled_date", "appointment_status"],
                name="appt_facility_status_idx",
            ),
        ]
