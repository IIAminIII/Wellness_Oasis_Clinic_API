from django.contrib import admin
from .models import Patient
# Register your models here.

class PatientModelAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "mobile_no"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "mobile_no",
    ]
    list_select_related = ["user"]

    @admin.display(description="Patient")
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

admin.site.register(Patient,PatientModelAdmin)
