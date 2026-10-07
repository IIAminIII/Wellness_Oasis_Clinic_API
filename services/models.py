from django.db import models

# Create your models here.

class Service(models.Model):
    name = models.CharField(max_length=80)
    description = models.TextField()
    image = models.ImageField(upload_to="services/image/", blank=True, null=True)
    specializations = models.ManyToManyField(
        "doctors.Specialization",
        blank=True,
        related_name="services",
        help_text="Doctor specializations that deliver this service.",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
