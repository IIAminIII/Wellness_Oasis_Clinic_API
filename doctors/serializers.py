from rest_framework import serializers

from .models import (
    AvailableTime,
    Designation,
    Doctor,
    DoctorLeave,
    Review,
    Specialization,
)


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ["id", "name", "slug"]


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["id", "name", "slug"]


class AvailableTimeSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(
        source="get_weekday_display",
        read_only=True,
    )

    class Meta:
        model = AvailableTime
        fields = [
            "id",
            "name",
            "weekday",
            "weekday_label",
            "start_time",
            "end_time",
            "capacity",
            "is_active",
        ]
        read_only_fields = ["id", "name", "weekday_label"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_time": "The slot must end after it starts."}
            )
        return attrs


class DoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    designation = DesignationSerializer(many=True, read_only=True)
    specialization = SpecializationSerializer(many=True, read_only=True)
    available_time = AvailableTimeSerializer(many=True, read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "full_name",
            "image",
            "designation",
            "specialization",
            "available_time",
            "fee",
            "bio",
            "is_accepting_patients",
        ]


class DoctorLeaveSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.__str__", read_only=True)

    class Meta:
        model = DoctorLeave
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "reviewed_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "doctor_name",
            "status",
            "reviewed_by",
            "created_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "Leave must end on or after it starts."}
            )
        return attrs


class DoctorLeaveDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            DoctorLeave.Status.APPROVED,
            DoctorLeave.Status.DECLINED,
        ]
    )


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(
        source="reviewer.user.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "reviewer_name",
            "doctor",
            "body",
            "created",
            "rating",
        ]
        read_only_fields = ["id", "reviewer_name", "created"]

    def validate(self, attrs):
        request = self.context.get("request")
        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        if request and request.user.is_authenticated and not self.instance:
            patient = getattr(request.user, "patient_profile", None)
            if patient and Review.objects.filter(
                reviewer=patient,
                doctor=doctor,
            ).exists():
                raise serializers.ValidationError(
                    "You have already reviewed this doctor."
                )
        return attrs
