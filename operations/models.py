from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Facility(models.Model):
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=40, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Dhaka")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "facilities"

    def __str__(self):
        return self.name


class Department(models.Model):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=40)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "code"],
                name="unique_department_code_per_facility",
            ),
        ]

    def __str__(self):
        return f"{self.facility}: {self.name}"


class Room(models.Model):
    class Kind(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        PROCEDURE = "procedure", "Procedure"
        WARD = "ward", "Ward"
        ICU = "icu", "Intensive care"
        LABORATORY = "laboratory", "Laboratory"

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="rooms",
        blank=True,
        null=True,
    )
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=120, blank=True)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.CONSULTATION,
    )
    floor = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility__name", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "number"],
                name="unique_room_number_per_facility",
            ),
        ]

    def clean(self):
        if self.department and self.facility_id != self.department.facility_id:
            raise ValidationError(
                {"department": "Department must belong to the selected facility."}
            )

    def __str__(self):
        return f"{self.facility}: room {self.number}"


class Bed(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        CLEANING = "cleaning", "Cleaning"
        OUT_OF_SERVICE = "out_of_service", "Out of service"

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="beds",
    )
    label = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["room__number", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "label"],
                name="unique_bed_label_per_room",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="bed_status_idx"),
        ]

    def __str__(self):
        return f"{self.room} bed {self.label}"


class RoleAssignment(models.Model):
    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        DOCTOR = "doctor", "Doctor"
        NURSE = "nurse", "Nurse"
        RECEPTIONIST = "receptionist", "Receptionist"
        BILLING = "billing", "Billing"
        LAB_TECHNICIAN = "lab_technician", "Lab technician"
        PHARMACIST = "pharmacist", "Pharmacist"
        ADMINISTRATOR = "administrator", "Administrator"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=24, choices=Role.choices)
    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="role_assignments",
        blank=True,
        null=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="role_assignments",
        blank=True,
        null=True,
    )
    employee_id = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(facility__isnull=True),
                name="unique_global_role_assignment",
            ),
            models.UniqueConstraint(
                fields=["user", "role", "facility"],
                condition=Q(facility__isnull=False),
                name="unique_facility_role_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["role", "is_active"], name="role_active_idx"),
            models.Index(fields=["facility", "role"], name="role_facility_idx"),
        ]

    def clean(self):
        if self.department and self.facility_id != self.department.facility_id:
            raise ValidationError(
                {"department": "Department must belong to the selected facility."}
            )

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"


class AuditEvent(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        blank=True,
        null=True,
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["target_type", "target_id", "-created_at"],
                name="audit_target_idx",
            ),
            models.Index(
                fields=["actor", "-created_at"],
                name="audit_actor_idx",
            ),
        ]

    @classmethod
    def record(
        cls,
        *,
        request,
        action,
        target,
        facility=None,
        metadata=None,
    ):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else request.META.get("REMOTE_ADDR")
        )
        return cls.objects.create(
            actor=request.user if request.user.is_authenticated else None,
            facility=facility,
            action=action,
            target_type=target._meta.label_lower,
            target_id=str(target.pk),
            metadata=metadata or {},
            ip_address=ip_address or None,
        )

    def __str__(self):
        return f"{self.action}: {self.target_type}#{self.target_id}"
