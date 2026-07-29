from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import Doctor
from operations.models import RoleAssignment
from .models import Service


class ServicePermissionTests(APITestCase):
    def test_public_can_read_but_not_create_services(self):
        Service.objects.create(name="Diagnostics", description="Lab services")

        list_response = self.client.get("/services/")
        create_response = self.client.post(
            "/services/",
            {"name": "Unsafe write", "description": "Should be rejected"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_administrator_can_create_services(self):
        administrator = User.objects.create_user(username="admin")
        RoleAssignment.objects.create(
            user=administrator,
            role=RoleAssignment.Role.ADMINISTRATOR,
        )
        self.client.force_authenticate(administrator)

        response = self.client.post(
            "/services/",
            {"name": "Cardiology", "description": "Heart care"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class DemoSeedTests(APITestCase):
    def test_seed_command_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)

        self.assertEqual(Service.objects.count(), 6)
        self.assertEqual(Doctor.objects.count(), 3)
