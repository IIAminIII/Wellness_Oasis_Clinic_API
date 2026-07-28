from rest_framework import serializers

from .models import AvailableTime, Designation, Doctor, Review, Specialization


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ["id", "name", "slug"]


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["id", "name", "slug"]


class AvailableTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableTime
        fields = ["id", "name"]


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
