from django.db import models

# Create your models here.

class ContactUs(models.Model):
    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    problem = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Contact Us"
        ordering = ["-created_at"]
