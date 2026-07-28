from rest_framework import serializers
from .models import ContactUs


class ContactUsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContactUs
        fields = ["id", "name", "phone", "email", "problem", "created_at"]
        read_only_fields = ["id", "created_at"]
