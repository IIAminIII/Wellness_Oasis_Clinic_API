from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "user_id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "mobile_no",
            "image",
        ]
        read_only_fields = ["id", "user_id", "username", "full_name"]

    def validate_email(self, value):
        queryset = User.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise serializers.ValidationError("An account already uses this email.")
        return value.lower()

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        if user_data:
            instance.user.save(update_fields=list(user_data))
        return super().update(instance, validated_data)


class RegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    mobile_no = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "mobile_no",
            "password",
            "confirm_password",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "The passwords do not match."}
            )
        candidate = User(
            username=attrs["username"],
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        validate_password(attrs["password"], user=candidate)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        mobile_no = validated_data.pop("mobile_no", "")
        password = validated_data.pop("password")
        is_active = self.context.get("activate_immediately", True)
        user = User(**validated_data, is_active=is_active)
        user.set_password(password)
        user.save()
        Patient.objects.create(user=user, mobile_no=mobile_no)
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username")
        if not identifier:
            raise serializers.ValidationError(
                {"identifier": "Enter your username or email address."}
            )
        attrs["identifier"] = identifier.strip()
        return attrs
