from django.utils import timezone
from rest_framework import serializers

from doctors.serializers import AvailableTimeSerializer, DoctorSerializer
from patients.serializers import PatientSerializer
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source="patient", read_only=True)
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)
    time_detail = AvailableTimeSerializer(source="time", read_only=True)

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
            "cancel",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "patient_detail",
            "doctor_detail",
            "time_detail",
            "appointment_status",
            "cancel",
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

        if doctor and not doctor.is_accepting_patients:
            raise serializers.ValidationError(
                {"doctor": "This doctor is not accepting appointments."}
            )
        if doctor and time and not doctor.available_time.filter(pk=time.pk).exists():
            raise serializers.ValidationError(
                {"time": "This time is not available for the selected doctor."}
            )

        collision = Appointment.objects.filter(
            doctor=doctor,
            time=time,
            scheduled_date=scheduled_date,
            cancel=False,
        )
        if self.instance:
            collision = collision.exclude(pk=self.instance.pk)
        if doctor and time and scheduled_date and collision.exists():
            raise serializers.ValidationError(
                {"time": "That appointment slot has just been booked."}
            )
        return attrs
