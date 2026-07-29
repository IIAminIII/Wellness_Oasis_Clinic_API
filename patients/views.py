from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from operations.models import RoleAssignment
from operations.permissions import has_any_role
from .models import Patient
from .serializers import (
    LoginSerializer,
    PatientSerializer,
    RegistrationSerializer,
    SessionUserSerializer,
)


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Patient.objects.select_related("user")
        if has_any_role(
            self.request.user,
            RoleAssignment.Role.ADMINISTRATOR,
        ):
            return queryset
        return queryset.filter(user=self.request.user)


class RegistrationApiView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"
    serializer_class = RegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data,
            context={
                "activate_immediately": not settings.REQUIRE_EMAIL_VERIFICATION,
            },
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if settings.REQUIRE_EMAIL_VERIFICATION:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            confirm_link = (
                f"{settings.BACKEND_URL}/patients/active/{uid}/{token}/"
            )
            body = render_to_string(
                "patientEmail.html",
                {"confirm_link": confirm_link, "user": user},
            )
            email = EmailMultiAlternatives(
                "Confirm your Wellness Oasis account",
                f"Confirm your account: {confirm_link}",
                to=[user.email],
            )
            email.attach_alternative(body, "text/html")
            email.send(fail_silently=False)
            return Response(
                {
                    "success": True,
                    "message": "Check your email to activate your account.",
                    "requires_verification": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        token = Token.objects.create(user=user)
        return Response(
            {
                "success": True,
                "message": "Your account is ready.",
                "token": token.key,
                "user": SessionUserSerializer(
                    user,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


def activate(_request, uid64, token):
    try:
        uid = urlsafe_base64_decode(uid64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        return redirect(f"{settings.FRONTEND_URL}/login.html?verified=1")
    return redirect(f"{settings.FRONTEND_URL}/login.html?verified=0")


class LoginApiView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]

        matching_user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        username = matching_user.username if matching_user else identifier
        user = authenticate(
            request=request,
            username=username,
            password=serializer.validated_data["password"],
        )
        if not user:
            return Response(
                {
                    "success": False,
                    "errors": {
                        "credentials": "The username/email or password is incorrect."
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "errors": {"account": "Activate your account before signing in."},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response(
            {
                "success": True,
                "token": token.key,
                "user": SessionUserSerializer(
                    user,
                    context={"request": request},
                ).data,
            }
        )


class LogOutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _patient_for(user):
        patient = getattr(user, "patient_profile", None)
        if not patient:
            raise PermissionDenied("A patient profile is required for this portal.")
        return patient

    def get(self, request):
        patient = self._patient_for(request.user)
        return Response(
            {"success": True, "user": PatientSerializer(patient).data}
        )

    def patch(self, request):
        patient = self._patient_for(request.user)
        serializer = PatientSerializer(
            patient,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "user": serializer.data})
