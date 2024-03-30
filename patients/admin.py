from django.contrib import admin
from .models import Patient
# Register your models here.

class PatientModelAdmin(admin.ModelAdmin):
    list_display = ['mobile_no','image']

    def first_name(self,obj):
        return obj.user.first_name
    def last_name(self,obj):
        return obj.user.last_name

admin.site.register(Patient,PatientModelAdmin)