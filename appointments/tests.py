from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import AvailableTime, Doctor
from operations.models import (
    AuditEvent,
    Department,
    Facility,
    RoleAssignment,
)
from patients.models import Patient
from .models import Appointment


class AppointmentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="patient",
            password="Healing!Pass2026",
        )
        self.patient = Patient.objects.create(user=self.user)
        doctor_user = User.objects.create_user(username="doctor")
        self.doctor = Doctor.objects.create(user=doctor_user, fee=1200)
        self.slot = AvailableTime.objects.create(name="09:00 - 09:30")
        self.other_slot = AvailableTime.objects.create(name="10:00 - 10:30")
        self.doctor.available_time.add(self.slot)
        self.client.force_authenticate(self.user)

    def test_patient_can_book_an_available_slot(self):
        response = self.client.post(
            "/appointments/list/",
            {
                "doctor": self.doctor.id,
                "appointment_type": "Offline",
                "symptoms": "Persistent headache",
                "scheduled_date": str(timezone.localdate() + timedelta(days=1)),
                "time": self.slot.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.appointment_status, "Pending")

    def test_unavailable_doctor_slot_is_rejected(self):
        response = self.client.post(
            "/appointments/list/",
            {
                "doctor": self.doctor.id,
                "appointment_type": "Online",
                "symptoms": "Follow-up",
                "scheduled_date": str(timezone.localdate() + timedelta(days=1)),
                "time": self.other_slot.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time", response.data["errors"])

    def test_patient_can_cancel_own_appointment(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_type="Offline",
            symptoms="Follow-up",
            scheduled_date=timezone.localdate() + timedelta(days=1),
            time=self.slot,
        )

        response = self.client.post(
            f"/appointments/list/{appointment.id}/cancel/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertTrue(appointment.cancel)
        self.assertEqual(appointment.appointment_status, "Cancelled")


class AppointmentOperationsTests(APITestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name="Wellness Oasis Main",
            code="main",
        )
        self.department = Department.objects.create(
            facility=self.facility,
            name="Cardiology",
            code="cardiology",
        )
        self.patient_user = User.objects.create_user(username="patient-two")
        self.patient = Patient.objects.create(user=self.patient_user)
        self.doctor_user = User.objects.create_user(username="doctor-two")
        self.doctor = Doctor.objects.create(user=self.doctor_user, fee=1500)
        RoleAssignment.objects.create(
            user=self.doctor_user,
            role=RoleAssignment.Role.DOCTOR,
            facility=self.facility,
            department=self.department,
        )
        self.slot = AvailableTime.objects.create(name="11:00 - 11:30")
        self.doctor.available_time.add(self.slot)
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_type=Appointment.Type.OFFLINE,
            symptoms="Chest discomfort",
            scheduled_date=timezone.localdate() + timedelta(days=1),
            time=self.slot,
            facility=self.facility,
            department=self.department,
        )

    def test_doctor_can_progress_own_appointment_with_audit_events(self):
        self.client.force_authenticate(self.doctor_user)

        for next_status in [
            Appointment.Status.CONFIRMED,
            Appointment.Status.RUNNING,
            Appointment.Status.COMPLETED,
        ]:
            response = self.client.post(
                f"/appointments/list/{self.appointment.id}/transition/",
                {"status": next_status},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.assertEqual(
            self.appointment.appointment_status,
            Appointment.Status.COMPLETED,
        )
        self.assertEqual(self.appointment.status_changed_by, self.doctor_user)
        self.assertEqual(
            AuditEvent.objects.filter(
                action="appointment.status_changed",
                target_id=str(self.appointment.id),
            ).count(),
            3,
        )

    def test_patient_cannot_transition_appointment(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            f"/appointments/list/{self.appointment.id}/transition/",
            {"status": Appointment.Status.CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_create_assisted_booking(self):
        receptionist = User.objects.create_user(username="reception-two")
        RoleAssignment.objects.create(
            user=receptionist,
            role=RoleAssignment.Role.RECEPTIONIST,
            facility=self.facility,
        )
        second_slot = AvailableTime.objects.create(name="13:00 - 13:30")
        self.doctor.available_time.add(second_slot)
        self.client.force_authenticate(receptionist)

        response = self.client.post(
            "/appointments/list/assisted/",
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "appointment_type": Appointment.Type.OFFLINE,
                "symptoms": "Reception desk booking",
                "scheduled_date": str(
                    timezone.localdate() + timedelta(days=2)
                ),
                "time": second_slot.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assisted = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(assisted.facility, self.facility)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="appointment.assisted_created",
                target_id=str(assisted.id),
            ).exists()
        )
