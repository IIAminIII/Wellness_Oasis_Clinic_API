from django.contrib import admin
from .models import ContactUs
# Register your models here.


class ContactModelAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "created_at", "resolved"]
    list_filter = ["resolved", "created_at"]
    search_fields = ["name", "phone", "email", "problem"]

admin.site.register(ContactUs,ContactModelAdmin)
