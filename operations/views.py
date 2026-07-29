from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

from .models import Department, Facility, RoleAssignment
from .permissions import IsAdministratorOrReadOnly, IsHospitalAdministrator
from .serializers import (
    CurrentActorSerializer,
    DepartmentSerializer,
    FacilitySerializer,
    RoleAssignmentSerializer,
)


class FacilityViewSet(viewsets.ModelViewSet):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    permission_classes = [IsAdministratorOrReadOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdministratorOrReadOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Department.objects.select_related("facility")
        facility_id = self.request.query_params.get("facility")
        if facility_id:
            queryset = queryset.filter(facility_id=facility_id)
        return queryset


class RoleAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = RoleAssignmentSerializer
    permission_classes = [IsHospitalAdministrator]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = RoleAssignment.objects.select_related(
            "user",
            "facility",
            "department",
        )
        role = self.request.query_params.get("role")
        facility_id = self.request.query_params.get("facility")
        if role:
            queryset = queryset.filter(role=role)
        if facility_id:
            queryset = queryset.filter(facility_id=facility_id)
        return queryset


class CurrentActorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "success": True,
                "user": CurrentActorSerializer(request.user).data,
            }
        )


class OperationsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assignments = request.user.role_assignments.filter(
            is_active=True
        ).select_related("facility", "department")
        roles = set(assignments.values_list("role", flat=True))
        today = timezone.localdate()

        appointments = Appointment.objects.select_related(
            "patient__user",
            "doctor__user",
            "time",
            "facility",
            "department",
        ).prefetch_related(
            "patient__user__role_assignments",
            "doctor__designation",
            "doctor__specialization",
            "doctor__available_time",
        )

        if RoleAssignment.Role.ADMINISTRATOR in roles:
            scope = "administrator"
        else:
            access_filter = Q(pk__in=[])
            scope = "personal"
            if RoleAssignment.Role.PATIENT in roles:
                access_filter |= Q(patient__user=request.user)
            if RoleAssignment.Role.DOCTOR in roles:
                access_filter |= Q(doctor__user=request.user)
                scope = "doctor"
            facility_ids = assignments.filter(
                role__in=[
                    RoleAssignment.Role.NURSE,
                    RoleAssignment.Role.RECEPTIONIST,
                ],
                facility__isnull=False,
            ).values_list("facility_id", flat=True)
            if facility_ids:
                access_filter |= Q(facility_id__in=facility_ids)
                scope = "operations"
            appointments = appointments.filter(access_filter).distinct()

        upcoming = appointments.filter(
            scheduled_date__gte=today,
            cancel=False,
        )
        stats = {
            "today": appointments.filter(scheduled_date=today, cancel=False).count(),
            "upcoming": upcoming.count(),
            "pending": appointments.filter(
                appointment_status=Appointment.Status.PENDING,
                cancel=False,
            ).count(),
            "confirmed": appointments.filter(
                appointment_status=Appointment.Status.CONFIRMED,
                cancel=False,
            ).count(),
            "completed": appointments.filter(
                appointment_status=Appointment.Status.COMPLETED,
            ).count(),
        }
        next_appointments = upcoming.order_by(
            "scheduled_date",
            "time__name",
        )[:8]
        return Response(
            {
                "success": True,
                "scope": scope,
                "roles": sorted(roles),
                "stats": stats,
                "appointments": AppointmentSerializer(
                    next_appointments,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )
