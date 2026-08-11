from django.utils import timezone
from rest_framework import serializers

from doctors.serializers import AvailableTimeSerializer, DoctorSerializer
from operations.serializers import DepartmentSerializer, FacilitySerializer
from patients.serializers import PatientSerializer
from patients.models import Patient
from .models import Appointment, WaitlistEntry
from .scheduling import slot_unavailable_reason


class AppointmentSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)
    time_detail = AvailableTimeSerializer(source="time", read_only=True)
    facility_detail = FacilitySerializer(source="facility", read_only=True)
    department_detail = DepartmentSerializer(source="department", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_detail",
            "doctor",
            "doctor_detail",
            "appointment_type",
            "appointment_status",
            "symptoms",
            "scheduled_date",
            "time",
            "time_detail",
            "facility",
            "facility_detail",
            "department",
            "department_detail",
            "cancel",
            "status_changed_by",
            "status_changed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "patient_detail",
            "doctor_detail",
            "time_detail",
            "facility",
            "facility_detail",
            "department",
            "department_detail",
            "appointment_status",
            "cancel",
            "status_changed_by",
            "status_changed_at",
            "created_at",
            "updated_at",
        ]

    def validate_scheduled_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Choose today or a future date.")
        return value

    def validate(self, attrs):
        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        time = attrs.get("time", getattr(self.instance, "time", None))
        scheduled_date = attrs.get(
            "scheduled_date",
            getattr(self.instance, "scheduled_date", None),
        )

        if doctor and time and scheduled_date:
            reason = slot_unavailable_reason(
                doctor=doctor,
                slot=time,
                scheduled_date=scheduled_date,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            if reason:
                field = "doctor" if doctor and not doctor.is_accepting_patients else "time"
                raise serializers.ValidationError({field: reason})
        return attrs


class AssistedAppointmentSerializer(AppointmentSerializer):
    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.select_related("user"),
    )

    class Meta(AppointmentSerializer.Meta):
        read_only_fields = [
            field
            for field in AppointmentSerializer.Meta.read_only_fields
            if field != "patient"
        ]


class AppointmentTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Appointment.Status.choices)


class WaitlistEntrySerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)
    time_detail = AvailableTimeSerializer(source="time", read_only=True)

    class Meta:
        model = WaitlistEntry
        fields = [
            "id",
            "patient",
            "patient_detail",
            "doctor",
            "doctor_detail",
            "time",
            "time_detail",
            "requested_date",
            "symptoms",
            "status",
            "appointment",
            "offered_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "patient_detail",
            "doctor_detail",
            "time_detail",
            "status",
            "appointment",
            "offered_at",
            "created_at",
        ]

    def validate_requested_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Choose today or a future date.")
        return value

    def validate(self, attrs):
        doctor = attrs.get("doctor")
        slot = attrs.get("time")
        requested_date = attrs.get("requested_date")
        if not (doctor and slot and requested_date):
            return attrs

        if slot.weekday != requested_date.weekday():
            raise serializers.ValidationError(
                {"time": "That slot does not run on the requested weekday."}
            )
        if not doctor.available_time.filter(pk=slot.pk).exists():
            raise serializers.ValidationError(
                {"time": "This time is not available for the selected doctor."}
            )
        # Joining a waitlist only makes sense once the slot is actually full.
        if not slot_unavailable_reason(
            doctor=doctor,
            slot=slot,
            scheduled_date=requested_date,
        ):
            raise serializers.ValidationError(
                {"time": "This slot is still open — book it directly instead."}
            )
        return attrs
