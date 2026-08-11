from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from Wellness_Oasis_Clinic.permissions import IsAdminOrReadOnly
from operations.models import AuditEvent, RoleAssignment
from operations.permissions import has_any_role
from .models import (
    AvailableTime,
    Designation,
    Doctor,
    DoctorLeave,
    Review,
    Specialization,
)
from .serializers import (
    AvailableTimeSerializer,
    DesignationSerializer,
    DoctorLeaveDecisionSerializer,
    DoctorLeaveSerializer,
    DoctorSerializer,
    ReviewSerializer,
    SpecializationSerializer,
)


class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "designation__name",
        "specialization__name",
    ]
    ordering_fields = ["fee", "user__first_name"]
    ordering = ["user__first_name"]

    def get_queryset(self):
        return (
            Doctor.objects.select_related("user")
            .prefetch_related("designation", "specialization", "available_time")
            .distinct()
        )


class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all().order_by("name")
    serializer_class = DesignationSerializer
    permission_classes = [IsAdminOrReadOnly]


class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all().order_by("name")
    serializer_class = SpecializationSerializer
    permission_classes = [IsAdminOrReadOnly]


class AvailableTimeForSpecificDoctor(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        doctor_id = request.query_params.get("doctor_id")
        if doctor_id:
            return queryset.filter(doctor__id=doctor_id).distinct()
        return queryset


class AvailableTimeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    queryset = AvailableTime.objects.all().order_by("name")
    serializer_class = AvailableTimeSerializer
    filter_backends = [AvailableTimeForSpecificDoctor]


class DoctorAvailabilityView(APIView):
    """Slot-by-slot openings for one doctor over a date window.

    Public, so the booking form can render a calendar before sign-in, but it
    only ever exposes counts — never who holds the other bookings.
    """

    permission_classes = [AllowAny]
    max_days = 30

    def get(self, request, doctor_id):
        from appointments.scheduling import (
            remaining_capacity,
            slot_unavailable_reason,
        )

        doctor = get_object_or_404(
            Doctor.objects.select_related("user").prefetch_related("available_time"),
            pk=doctor_id,
        )
        today = timezone.localdate()
        start = parse_date(request.query_params.get("from", "")) or today
        start = max(start, today)
        try:
            days = int(request.query_params.get("days", 7))
        except ValueError:
            raise ValidationError({"days": "Provide a whole number of days."})
        days = max(1, min(days, self.max_days))

        slots_by_weekday = {}
        for slot in doctor.available_time.filter(is_active=True):
            slots_by_weekday.setdefault(slot.weekday, []).append(slot)

        calendar = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            openings = []
            for slot in sorted(
                slots_by_weekday.get(day.weekday(), []),
                key=lambda item: item.start_time,
            ):
                reason = slot_unavailable_reason(
                    doctor=doctor,
                    slot=slot,
                    scheduled_date=day,
                )
                openings.append(
                    {
                        "time": slot.pk,
                        "label": slot.name,
                        "start_time": slot.start_time,
                        "end_time": slot.end_time,
                        "capacity": slot.capacity,
                        "remaining": remaining_capacity(
                            doctor=doctor,
                            slot=slot,
                            scheduled_date=day,
                        ),
                        "bookable": reason is None,
                        "reason": reason,
                    }
                )
            calendar.append(
                {
                    "date": day,
                    "on_leave": doctor.is_on_leave(day),
                    "slots": openings,
                }
            )
        return Response(
            {"success": True, "doctor": doctor.pk, "days": calendar}
        )


class DoctorLeaveViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorLeaveSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "decide":
            return DoctorLeaveDecisionSerializer
        return DoctorLeaveSerializer

    def _is_administrator(self):
        return has_any_role(self.request.user, RoleAssignment.Role.ADMINISTRATOR)

    def get_queryset(self):
        queryset = DoctorLeave.objects.select_related("doctor__user", "reviewed_by")
        if not self._is_administrator():
            queryset = queryset.filter(doctor__user=self.request.user)
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset

    def perform_create(self, serializer):
        doctor = serializer.validated_data.get("doctor")
        own_profile = getattr(self.request.user, "doctor_profile", None)
        if not self._is_administrator() and doctor != own_profile:
            raise PermissionDenied("You can only request your own leave.")
        serializer.save()

    def perform_update(self, serializer):
        if (
            not self._is_administrator()
            and serializer.instance.status != DoctorLeave.Status.REQUESTED
        ):
            raise PermissionDenied("Reviewed leave can no longer be edited.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        if not self._is_administrator():
            raise PermissionDenied("Administrator access is required.")
        leave = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave.status = serializer.validated_data["status"]
        leave.reviewed_by = request.user
        leave.save(update_fields=["status", "reviewed_by", "updated_at"])
        AuditEvent.record(
            request=request,
            action="doctor_leave.decided",
            target=leave,
            metadata={"status": leave.status},
        )
        return Response(
            {"success": True, "leave": DoctorLeaveSerializer(leave).data}
        )


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Review.objects.select_related("reviewer__user", "doctor__user")
        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset

    def perform_create(self, serializer):
        patient = getattr(self.request.user, "patient_profile", None)
        if not patient:
            raise ValidationError("A patient profile is required to add a review.")
        serializer.save(reviewer=patient)

    def _ensure_owner(self, instance):
        if (
            not has_any_role(
                self.request.user,
                RoleAssignment.Role.ADMINISTRATOR,
            )
            and instance.reviewer.user_id != self.request.user.id
        ):
            raise PermissionDenied("You can only change your own review.")

    def perform_update(self, serializer):
        self._ensure_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_owner(instance)
        instance.delete()
