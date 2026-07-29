from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from operations.models import RoleAssignment
from .models import Patient


class AuthenticationFlowTests(APITestCase):
    registration_payload = {
        "username": "amina",
        "first_name": "Amina",
        "last_name": "Rahman",
        "email": "amina@example.com",
        "mobile_no": "+8801700000000",
        "password": "Healing!Pass2026",
        "confirm_password": "Healing!Pass2026",
    }

    def test_registration_creates_patient_and_returns_token(self):
        response = self.client.post(
            "/patients/register/",
            self.registration_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("token", response.data)
        user = User.objects.get(username="amina")
        self.assertTrue(Patient.objects.filter(user=user).exists())
        self.assertTrue(
            RoleAssignment.objects.filter(
                user=user,
                role=RoleAssignment.Role.PATIENT,
                is_active=True,
            ).exists()
        )
        self.assertIn("patient", response.data["user"]["roles"])

    def test_login_profile_and_logout_flow(self):
        user = User.objects.create_user(
            username="karim",
            email="karim@example.com",
            password="Healing!Pass2026",
            first_name="Karim",
        )
        Patient.objects.create(user=user)

        login_response = self.client.post(
            "/patients/login/",
            {"identifier": "KARIM@EXAMPLE.COM", "password": "Healing!Pass2026"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        profile_response = self.client.get("/patients/me/")
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["user"]["username"], "karim")

        logout_response = self.client.post("/patients/logout/")
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existing",
            email="amina@example.com",
            password="Healing!Pass2026",
        )

        response = self.client.post(
            "/patients/register/",
            self.registration_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_staff_login_does_not_create_patient_profile(self):
        receptionist = User.objects.create_user(
            username="reception",
            email="reception@example.com",
            password="Healing!Pass2026",
        )
        RoleAssignment.objects.create(
            user=receptionist,
            role=RoleAssignment.Role.RECEPTIONIST,
        )

        response = self.client.post(
            "/patients/login/",
            {
                "identifier": "reception@example.com",
                "password": "Healing!Pass2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Patient.objects.filter(user=receptionist).exists())
        self.assertIn("receptionist", response.data["user"]["roles"])
