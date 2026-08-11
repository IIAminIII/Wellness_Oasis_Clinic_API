from django.contrib import admin

from .models import AuditEvent, Bed, Department, Facility, RoleAssignment, Room


class BedInline(admin.TabularInline):
    model = Bed
    extra = 0


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "facility", "department", "kind", "is_active"]
    list_filter = ["facility", "kind", "is_active"]
    search_fields = ["number", "name"]
    inlines = [BedInline]


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ["label", "room", "status"]
    list_filter = ["status", "room__facility"]
    search_fields = ["label", "room__number"]


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "timezone", "is_active"]
    list_filter = ["is_active", "timezone"]
    search_fields = ["name", "code", "address"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "facility", "code", "is_active"]
    list_filter = ["facility", "is_active"]
    search_fields = ["name", "code"]


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "role",
        "facility",
        "department",
        "employee_id",
        "is_active",
    ]
    list_filter = ["role", "facility", "department", "is_active"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "employee_id",
    ]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "actor",
        "action",
        "target_type",
        "target_id",
        "facility",
    ]
    list_filter = ["action", "target_type", "facility"]
    search_fields = ["actor__username", "target_id"]
    readonly_fields = [
        "actor",
        "facility",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "ip_address",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
