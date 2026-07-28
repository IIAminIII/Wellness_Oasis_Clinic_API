from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Appointment.objects.select_related(
            "patient__user",
            "doctor__user",
            "time",
        ).prefetch_related(
            "doctor__designation",
            "doctor__specialization",
            "doctor__available_time",
        )
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(
            Q(patient__user=user) | Q(doctor__user=user)
        ).distinct()

    def perform_create(self, serializer):
        patient = getattr(self.request.user, "patient_profile", None)
        if not patient:
            raise ValidationError("A patient profile is required to book.")
        serializer.save(patient=patient)

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied(
                "Use the cancellation action to change an appointment."
            )
        serializer.save()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        is_owner = appointment.patient.user_id == request.user.id
        if not (is_owner or request.user.is_staff):
            raise PermissionDenied("You cannot cancel this appointment.")
        if appointment.appointment_status == Appointment.Status.COMPLETED:
            raise ValidationError("A completed appointment cannot be cancelled.")
        appointment.cancel = True
        appointment.appointment_status = Appointment.Status.CANCELLED
        appointment.save(
            update_fields=["cancel", "appointment_status", "updated_at"]
        )
        return Response(
            {"success": True, "appointment": self.get_serializer(appointment).data},
            status=status.HTTP_200_OK,
        )
