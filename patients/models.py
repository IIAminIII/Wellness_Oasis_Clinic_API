from django.contrib.auth.models import User
from django.db import models


class Patient(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    image = models.ImageField(
        upload_to="patients/images/",
        blank=True,
        null=True,
    )
    mobile_no = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
