from django.contrib.auth.models import User
from django.db import models

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


class AvailableTime(models.Model):
    name = models.CharField(max_length=100)

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

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


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
