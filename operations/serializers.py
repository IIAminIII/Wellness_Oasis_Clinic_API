from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Department, Facility, RoleAssignment


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "code",
            "address",
            "phone",
            "timezone",
            "is_active",
        ]


class DepartmentSerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source="facility.name", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "facility",
            "facility_name",
            "name",
            "code",
            "description",
            "is_active",
        ]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "username",
            "full_name",
            "role",
            "role_label",
            "facility",
            "facility_name",
            "department",
            "department_name",
            "employee_id",
            "is_active",
        ]

    def validate(self, attrs):
        facility = attrs.get("facility", getattr(self.instance, "facility", None))
        department = attrs.get(
            "department",
            getattr(self.instance, "department", None),
        )
        if department and department.facility_id != getattr(facility, "id", None):
            raise serializers.ValidationError(
                {"department": "Department must belong to the selected facility."}
            )
        request = self.context.get("request")
        if (
            self.instance
            and request
            and self.instance.user_id == request.user.id
            and self.instance.role == RoleAssignment.Role.ADMINISTRATOR
        ):
            next_role = attrs.get("role", self.instance.role)
            next_active = attrs.get("is_active", self.instance.is_active)
            if (
                next_role != RoleAssignment.Role.ADMINISTRATOR
                or not next_active
            ):
                raise serializers.ValidationError(
                    "You cannot remove your own administrator access."
                )
        return attrs


class CurrentActorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "roles",
        ]

    def get_roles(self, user):
        assignments = user.role_assignments.filter(is_active=True).select_related(
            "facility",
            "department",
        )
        return RoleAssignmentSerializer(assignments, many=True).data
