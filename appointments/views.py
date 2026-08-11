from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from operations.models import AuditEvent, RoleAssignment
from operations.permissions import active_roles, has_any_role
from .models import Appointment, WaitlistEntry
from .scheduling import offer_freed_slot, slot_unavailable_reason
from .serializers import (
    AppointmentSerializer,
    AppointmentTransitionSerializer,
    AssistedAppointmentSerializer,
    WaitlistEntrySerializer,
)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "assisted":
            return AssistedAppointmentSerializer
        if self.action == "transition":
            return AppointmentTransitionSerializer
        return AppointmentSerializer

    def get_queryset(self):
        queryset = Appointment.objects.select_related(
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
        user = self.request.user
        roles = active_roles(user)
        if RoleAssignment.Role.ADMINISTRATOR in roles:
            return queryset

        access_filter = Q(patient__user=user) | Q(doctor__user=user)
        facility_ids = user.role_assignments.filter(
            is_active=True,
            role__in=[
                RoleAssignment.Role.NURSE,
                RoleAssignment.Role.RECEPTIONIST,
            ],
            facility__isnull=False,
        ).values_list("facility_id", flat=True)
        if facility_ids:
            access_filter |= Q(facility_id__in=facility_ids)
        return queryset.filter(access_filter).distinct()

    @staticmethod
    def _doctor_location(doctor):
        assignment = doctor.user.role_assignments.filter(
            role=RoleAssignment.Role.DOCTOR,
            is_active=True,
            facility__isnull=False,
        ).select_related("facility", "department").first()
        if not assignment:
            return None, None
        return assignment.facility, assignment.department

    def perform_create(self, serializer):
        patient = getattr(self.request.user, "patient_profile", None)
        if not patient:
            raise ValidationError("A patient profile is required to book.")
        facility, department = self._doctor_location(
            serializer.validated_data["doctor"]
        )
        appointment = serializer.save(
            patient=patient,
            facility=facility,
            department=department,
        )
        AuditEvent.record(
            request=self.request,
            action="appointment.created",
            target=appointment,
            facility=facility,
        )

    def perform_update(self, serializer):
        if not has_any_role(
            self.request.user,
            RoleAssignment.Role.ADMINISTRATOR,
        ):
            raise PermissionDenied(
                "Use an appointment workflow action to make changes."
            )
        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        appointment = self.get_object()
        AuditEvent.record(
            request=request,
            action="appointment.viewed",
            target=appointment,
            facility=appointment.facility,
        )
        return Response(self.get_serializer(appointment).data)

    @action(detail=False, methods=["post"])
    def assisted(self, request):
        if not has_any_role(
            request.user,
            RoleAssignment.Role.RECEPTIONIST,
            RoleAssignment.Role.ADMINISTRATOR,
        ):
            raise PermissionDenied(
                "Reception or administration access is required."
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        facility, department = self._doctor_location(
            serializer.validated_data["doctor"]
        )
        appointment = serializer.save(
            facility=facility,
            department=department,
        )
        AuditEvent.record(
            request=request,
            action="appointment.assisted_created",
            target=appointment,
            facility=facility,
        )
        return Response(
            AppointmentSerializer(
                appointment,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def transition(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=pk,
        )
        next_status = serializer.validated_data["status"]
        allowed_transitions = {
            Appointment.Status.PENDING: {
                Appointment.Status.CONFIRMED,
                Appointment.Status.CANCELLED,
            },
            Appointment.Status.CONFIRMED: {
                Appointment.Status.RUNNING,
                Appointment.Status.CANCELLED,
            },
            Appointment.Status.RUNNING: {
                Appointment.Status.COMPLETED,
                Appointment.Status.CANCELLED,
            },
        }
        if next_status not in allowed_transitions.get(
            appointment.appointment_status,
            set(),
        ):
            raise ValidationError(
                {
                    "status": (
                        f"Cannot move from {appointment.appointment_status} "
                        f"to {next_status}."
                    )
                }
            )

        roles = active_roles(request.user)
        doctor_owns_appointment = (
            RoleAssignment.Role.DOCTOR in roles
            and appointment.doctor.user_id == request.user.id
        )
        allowed_for_role = (
            RoleAssignment.Role.ADMINISTRATOR in roles
            or (
                RoleAssignment.Role.RECEPTIONIST in roles
                and next_status
                in {
                    Appointment.Status.CONFIRMED,
                    Appointment.Status.CANCELLED,
                }
            )
            or (
                doctor_owns_appointment
                and next_status
                in {
                    Appointment.Status.CONFIRMED,
                    Appointment.Status.RUNNING,
                    Appointment.Status.COMPLETED,
                    Appointment.Status.CANCELLED,
                }
            )
            or (
                RoleAssignment.Role.NURSE in roles
                and next_status == Appointment.Status.RUNNING
            )
        )
        if not allowed_for_role:
            raise PermissionDenied(
                "Your hospital role cannot perform this transition."
            )

        previous_status = appointment.appointment_status
        appointment.appointment_status = next_status
        appointment.cancel = next_status == Appointment.Status.CANCELLED
        appointment.status_changed_by = request.user
        appointment.status_changed_at = timezone.now()
        appointment.save(
            update_fields=[
                "appointment_status",
                "cancel",
                "status_changed_by",
                "status_changed_at",
                "updated_at",
            ]
        )
        AuditEvent.record(
            request=request,
            action="appointment.status_changed",
            target=appointment,
            facility=appointment.facility,
            metadata={"from": previous_status, "to": next_status},
        )
        if next_status == Appointment.Status.CANCELLED:
            offer_freed_slot(appointment)
        return Response(
            {
                "success": True,
                "appointment": AppointmentSerializer(
                    appointment,
                    context={"request": request},
                ).data,
            }
        )

    @action(detail=False, methods=["get"])
    def waitlist_offers(self, request):
        """Offers currently held by the signed-in patient."""
        patient = getattr(request.user, "patient_profile", None)
        entries = WaitlistEntry.objects.none()
        if patient:
            entries = WaitlistEntry.objects.filter(
                patient=patient,
                status=WaitlistEntry.Status.OFFERED,
            ).select_related("doctor__user", "time", "patient__user")
        return Response(
            {
                "success": True,
                "offers": WaitlistEntrySerializer(entries, many=True).data,
            }
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        is_owner = appointment.patient.user_id == request.user.id
        can_manage = has_any_role(
            request.user,
            RoleAssignment.Role.RECEPTIONIST,
            RoleAssignment.Role.ADMINISTRATOR,
        )
        if not (is_owner or can_manage):
            raise PermissionDenied("You cannot cancel this appointment.")
        if appointment.appointment_status == Appointment.Status.COMPLETED:
            raise ValidationError("A completed appointment cannot be cancelled.")
        appointment.cancel = True
        appointment.appointment_status = Appointment.Status.CANCELLED
        appointment.status_changed_by = request.user
        appointment.status_changed_at = timezone.now()
        appointment.save(
            update_fields=[
                "cancel",
                "appointment_status",
                "status_changed_by",
                "status_changed_at",
                "updated_at",
            ]
        )
        AuditEvent.record(
            request=request,
            action="appointment.cancelled",
            target=appointment,
            facility=appointment.facility,
        )
        offer_freed_slot(appointment)
        return Response(
            {"success": True, "appointment": self.get_serializer(appointment).data},
            status=status.HTTP_200_OK,
        )


class WaitlistEntryViewSet(viewsets.ModelViewSet):
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = WaitlistEntry.objects.select_related(
            "patient__user",
            "doctor__user",
            "time",
        )
        user = self.request.user
        roles = active_roles(user)
        if roles.intersection(
            {
                RoleAssignment.Role.ADMINISTRATOR,
                RoleAssignment.Role.RECEPTIONIST,
            }
        ):
            doctor_id = self.request.query_params.get("doctor")
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            return queryset
        return queryset.filter(
            Q(patient__user=user) | Q(doctor__user=user)
        ).distinct()

    def perform_create(self, serializer):
        patient = getattr(self.request.user, "patient_profile", None)
        if not patient:
            raise ValidationError("A patient profile is required to join a waitlist.")
        entry = serializer.save(patient=patient)
        AuditEvent.record(
            request=self.request,
            action="waitlist.joined",
            target=entry,
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Convert an offer into a real appointment, if it is still free.

        The booking runs in its own transaction so that the row lock covers the
        capacity re-check. Expiring a stale offer happens *after* that block —
        raising inside it would roll the expiry back and leave the offer open.
        """
        with transaction.atomic():
            entry = get_object_or_404(
                self.get_queryset().select_for_update(),
                pk=pk,
            )
            if entry.patient.user_id != request.user.id:
                raise PermissionDenied("This offer belongs to another patient.")
            if entry.status != WaitlistEntry.Status.OFFERED:
                raise ValidationError("This waitlist entry has no open offer.")

            reason = slot_unavailable_reason(
                doctor=entry.doctor,
                slot=entry.time,
                scheduled_date=entry.requested_date,
            )
            if not reason:
                facility, department = AppointmentViewSet._doctor_location(
                    entry.doctor
                )
                appointment = Appointment.objects.create(
                    patient=entry.patient,
                    doctor=entry.doctor,
                    appointment_type=Appointment.Type.OFFLINE,
                    symptoms=entry.symptoms or "Booked from the waitlist.",
                    scheduled_date=entry.requested_date,
                    time=entry.time,
                    facility=facility,
                    department=department,
                )
                entry.status = WaitlistEntry.Status.BOOKED
                entry.appointment = appointment
                entry.save(
                    update_fields=["status", "appointment", "updated_at"]
                )
                AuditEvent.record(
                    request=request,
                    action="waitlist.accepted",
                    target=appointment,
                    facility=facility,
                )
                return Response(
                    {
                        "success": True,
                        "appointment": AppointmentSerializer(
                            appointment,
                            context={"request": request},
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        entry.status = WaitlistEntry.Status.EXPIRED
        entry.save(update_fields=["status", "updated_at"])
        raise ValidationError({"time": reason})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        entry = self.get_object()
        if entry.patient.user_id != request.user.id and not has_any_role(
            request.user,
            RoleAssignment.Role.RECEPTIONIST,
            RoleAssignment.Role.ADMINISTRATOR,
        ):
            raise PermissionDenied("You cannot change this waitlist entry.")
        if entry.status == WaitlistEntry.Status.BOOKED:
            raise ValidationError("This entry has already been booked.")
        entry.status = WaitlistEntry.Status.CANCELLED
        entry.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "entry": self.get_serializer(entry).data})
