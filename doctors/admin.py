from django.contrib import admin
from .models import (
    Specialization,
    Designation,
    AvailableTime,
    Doctor,
    DoctorLeave,
    Review,
)
# Register your models here.
class SpecializationAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(Specialization,SpecializationAdmin)
class DesignationAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(Designation,DesignationAdmin)
class AvailableTimeAdmin(admin.ModelAdmin):
    list_display = ["name", "weekday", "start_time", "end_time", "capacity", "is_active"]
    list_filter = ["weekday", "is_active"]
    readonly_fields = ["name"]
admin.site.register(AvailableTime, AvailableTimeAdmin)


class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ["doctor", "start_date", "end_date", "status", "reviewed_by"]
    list_filter = ["status", "start_date"]
    search_fields = ["doctor__user__first_name", "doctor__user__last_name"]
    list_select_related = ["doctor__user", "reviewed_by"]
admin.site.register(DoctorLeave, DoctorLeaveAdmin)

admin.site.register(Doctor)
admin.site.register(Review)