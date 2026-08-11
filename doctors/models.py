from datetime import time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from patients.models import Patient


class Specialization(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(max_length=40)

    def __str__(self):
        return self.name


class Designation(models.Model):
    name = models.CharField(max_length=30)
    slug = models.SlugField(max_length=40)

    def __str__(self):
        return self.name


class Weekday(models.IntegerChoices):
    """Matches ``datetime.date.weekday()`` so scheduling maths stays trivial."""

    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class AvailableTime(models.Model):
    """A recurring weekly slot template that doctors can be attached to."""

    name = models.CharField(max_length=100)
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        default=Weekday.SATURDAY,
    )
    start_time = models.TimeField(default=time(9, 0))
    end_time = models.TimeField(default=time(17, 0))
    capacity = models.PositiveSmallIntegerField(
        default=1,
        help_text="How many patients one doctor can see in this slot.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["weekday", "start_time", "end_time"],
                name="unique_slot_template",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F("start_time")),
                name="slot_ends_after_it_starts",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1),
                name="slot_capacity_at_least_one",
            ),
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError(
                {"end_time": "The slot must end after it starts."}
            )

    @property
    def label(self):
        return (
            f"{Weekday(self.weekday).label} "
            f"{self.start_time:%H:%M} - {self.end_time:%H:%M}"
        )

    def save(self, *args, **kwargs):
        self.name = self.label
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    image = models.ImageField(
        upload_to="doctors/images/",
        blank=True,
        null=True,
    )
    designation = models.ManyToManyField(Designation)
    specialization = models.ManyToManyField(Specialization)
    available_time = models.ManyToManyField(AvailableTime)
    fee = models.PositiveIntegerField()
    meet_link = models.URLField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    is_accepting_patients = models.BooleanField(default=True)

    def is_on_leave(self, on_date):
        return self.leave.filter(
            status=DoctorLeave.Status.APPROVED,
            start_date__lte=on_date,
            end_date__gte=on_date,
        ).exists()

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class DoctorLeave(models.Model):
    """A date range in which a doctor cannot be booked."""

    class Status(models.TextChoices):
        REQUESTED = "Requested", "Requested"
        APPROVED = "Approved", "Approved"
        DECLINED = "Declined", "Declined"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="leave",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="reviewed_doctor_leave",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="leave_ends_on_or_after_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=["doctor", "status", "start_date", "end_date"],
                name="leave_doctor_window_idx",
            ),
        ]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "Leave must end on or after it starts."}
            )

    def __str__(self):
        return f"{self.doctor}: {self.start_date} to {self.end_date}"


class Review(models.Model):
    reviewer = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    body = models.TextField(max_length=2000)
    created = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveSmallIntegerField(
        choices=[(value, str(value)) for value in range(1, 6)]
    )

    def __str__(self):
        return (
            f"Patient: {self.reviewer}; "
            f"Doctor: {self.doctor}; Rating: {self.rating}"
        )

    class Meta:
        ordering = ["-created"]
