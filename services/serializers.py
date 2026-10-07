from rest_framework import serializers

from doctors.serializers import SpecializationSerializer
from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    specializations = SpecializationSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = ["id", "name", "description", "image", "specializations"]