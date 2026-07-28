from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import AvailableTime, Doctor
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
