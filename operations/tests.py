from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from doctors.models import AvailableTime, Doctor
from patients.models import Patient

from .models import Department, Facility, RoleAssignment


class OperationsAccessTests(APITestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name="Wellness Oasis Main",
            code="main",
        )
        self.department = Department.objects.create(
            facility=self.facility,
            name="General Medicine",
            code="general-medicine",
        )

    def test_current_actor_returns_explicit_roles(self):
        nurse = User.objects.create_user(username="nurse")
        RoleAssignment.objects.create(
            user=nurse,
            role=RoleAssignment.Role.NURSE,
            facility=self.facility,
            department=self.department,
            employee_id="N-1001",
        )
        self.client.force_authenticate(nurse)

        response = self.client.get("/operations/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["roles"][0]["role"], "nurse")
        self.assertEqual(
            response.data["user"]["roles"][0]["facility_name"],
            "Wellness Oasis Main",
        )

    def test_only_administrator_can_create_facility(self):
        receptionist = User.objects.create_user(username="reception")
        RoleAssignment.objects.create(
            user=receptionist,
            role=RoleAssignment.Role.RECEPTIONIST,
            facility=self.facility,
        )
        self.client.force_authenticate(receptionist)
        denied = self.client.post(
            "/operations/facilities/",
            {"name": "Branch", "code": "branch"},
            format="json",
        )

        administrator = User.objects.create_user(username="administrator")
        RoleAssignment.objects.create(
            user=administrator,
            role=RoleAssignment.Role.ADMINISTRATOR,
        )
        self.client.force_authenticate(administrator)
        allowed = self.client.post(
            "/operations/facilities/",
            {"name": "Branch", "code": "branch"},
            format="json",
        )

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

    def test_administrator_cannot_remove_own_access(self):
        administrator = User.objects.create_user(username="self-admin")
        assignment = RoleAssignment.objects.create(
            user=administrator,
            role=RoleAssignment.Role.ADMINISTRATOR,
        )
        self.client.force_authenticate(administrator)

        response = self.client.patch(
            f"/operations/roles/{assignment.id}/",
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assignment.refresh_from_db()
        self.assertTrue(assignment.is_active)

    def test_receptionist_dashboard_is_scoped_to_facility(self):
        receptionist = User.objects.create_user(username="desk")
        RoleAssignment.objects.create(
            user=receptionist,
            role=RoleAssignment.Role.RECEPTIONIST,
            facility=self.facility,
        )
        patient_user = User.objects.create_user(username="dashboard-patient")
        patient = Patient.objects.create(user=patient_user)
        doctor_user = User.objects.create_user(username="dashboard-doctor")
        doctor = Doctor.objects.create(user=doctor_user, fee=1000)
        slot = AvailableTime.objects.create(name="15:00 - 15:30")
        doctor.available_time.add(slot)
        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_type=Appointment.Type.OFFLINE,
            symptoms="Routine check",
            scheduled_date=timezone.localdate() + timedelta(days=1),
            time=slot,
            facility=self.facility,
            department=self.department,
        )
        self.client.force_authenticate(receptionist)

        response = self.client.get("/operations/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["scope"], "operations")
        self.assertEqual(response.data["stats"]["upcoming"], 1)
        self.assertEqual(len(response.data["appointments"]), 1)
