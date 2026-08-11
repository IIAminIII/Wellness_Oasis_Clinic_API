from datetime import time, timedelta

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from doctors.models import Doctor, DoctorLeave
from doctors.testing import make_slot, next_date_for
from patients.models import Patient
from .models import Appointment, WaitlistEntry


class SchedulingCapacityTests(APITestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(username="capacity-doctor")
        self.doctor = Doctor.objects.create(user=self.doctor_user, fee=900)
        self.slot = make_slot(
            weekday=1,
            start=time(9, 0),
            end=time(12, 0),
            capacity=2,
        )
        self.doctor.available_time.add(self.slot)
        self.slot_date = next_date_for(self.slot)

    def _book_as(self, username, on_date=None):
        user = User.objects.create_user(username=username)
        Patient.objects.create(user=user)
        self.client.force_authenticate(user)
        return self.client.post(
            "/appointments/list/",
            {
                "doctor": self.doctor.id,
                "appointment_type": "Offline",
                "symptoms": "Assessment",
                "scheduled_date": str(on_date or self.slot_date),
                "time": self.slot.id,
            },
            format="json",
        )

    def test_slot_accepts_bookings_up_to_capacity(self):
        self.assertEqual(
            self._book_as("cap-a").status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self._book_as("cap-b").status_code,
            status.HTTP_201_CREATED,
        )

    def test_booking_beyond_capacity_is_rejected(self):
        self._book_as("cap-c")
        self._book_as("cap-d")

        response = self._book_as("cap-e")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fully booked", str(response.data["errors"]["time"]))

    def test_cancelling_frees_capacity_again(self):
        self._book_as("cap-f")
        self._book_as("cap-g")
        appointment = Appointment.objects.first()
        appointment.cancel = True
        appointment.appointment_status = Appointment.Status.CANCELLED
        appointment.save()

        self.assertEqual(
            self._book_as("cap-h").status_code,
            status.HTTP_201_CREATED,
        )

    def test_slot_cannot_be_booked_on_the_wrong_weekday(self):
        response = self._book_as("cap-i", on_date=self.slot_date + timedelta(days=1))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("only runs on", str(response.data["errors"]["time"]))

    def test_doctor_on_approved_leave_cannot_be_booked(self):
        DoctorLeave.objects.create(
            doctor=self.doctor,
            start_date=self.slot_date,
            end_date=self.slot_date,
            status=DoctorLeave.Status.APPROVED,
        )

        response = self._book_as("cap-j")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("on leave", str(response.data["errors"]["time"]))

    def test_requested_leave_does_not_block_booking(self):
        DoctorLeave.objects.create(
            doctor=self.doctor,
            start_date=self.slot_date,
            end_date=self.slot_date,
            status=DoctorLeave.Status.REQUESTED,
        )

        self.assertEqual(
            self._book_as("cap-k").status_code,
            status.HTTP_201_CREATED,
        )

    def test_availability_endpoint_reports_remaining_places(self):
        self._book_as("cap-l")
        self.client.force_authenticate(None)

        response = self.client.get(
            f"/doctors/list/{self.doctor.id}/availability/",
            {"from": str(self.slot_date), "days": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        day = response.data["days"][0]
        self.assertEqual(day["slots"][0]["remaining"], 1)
        self.assertTrue(day["slots"][0]["bookable"])

    def test_availability_marks_full_slots_unbookable(self):
        self._book_as("cap-m")
        self._book_as("cap-n")
        self.client.force_authenticate(None)

        response = self.client.get(
            f"/doctors/list/{self.doctor.id}/availability/",
            {"from": str(self.slot_date), "days": 1},
        )

        slot = response.data["days"][0]["slots"][0]
        self.assertEqual(slot["remaining"], 0)
        self.assertFalse(slot["bookable"])


class WaitlistTests(APITestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(username="waitlist-doctor")
        self.doctor = Doctor.objects.create(user=self.doctor_user, fee=900)
        self.slot = make_slot(
            weekday=4,
            start=time(9, 0),
            end=time(10, 0),
            capacity=1,
        )
        self.doctor.available_time.add(self.slot)
        self.slot_date = next_date_for(self.slot)

        self.holder = User.objects.create_user(username="slot-holder")
        self.holder_patient = Patient.objects.create(user=self.holder)
        self.appointment = Appointment.objects.create(
            patient=self.holder_patient,
            doctor=self.doctor,
            appointment_type=Appointment.Type.OFFLINE,
            symptoms="First in",
            scheduled_date=self.slot_date,
            time=self.slot,
        )

        self.waiter = User.objects.create_user(username="waiter")
        self.waiter_patient = Patient.objects.create(user=self.waiter)

    def _join(self):
        self.client.force_authenticate(self.waiter)
        return self.client.post(
            "/appointments/waitlist/",
            {
                "doctor": self.doctor.id,
                "time": self.slot.id,
                "requested_date": str(self.slot_date),
                "symptoms": "Please call me",
            },
            format="json",
        )

    def _cancel_holder_appointment(self):
        self.client.force_authenticate(self.holder)
        self.client.post(f"/appointments/list/{self.appointment.id}/cancel/")

    def test_patient_can_join_a_full_slot_waitlist(self):
        response = self._join()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.patient, self.waiter_patient)
        self.assertEqual(entry.status, WaitlistEntry.Status.WAITING)

    def test_joining_an_open_slot_is_rejected(self):
        self.appointment.delete()

        response = self._join()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("still open", str(response.data["errors"]["time"]))

    def test_cancellation_offers_the_slot_to_the_first_waiter(self):
        self._join()

        self._cancel_holder_appointment()

        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.status, WaitlistEntry.Status.OFFERED)
        self.assertIsNotNone(entry.offered_at)

    def test_waiter_can_accept_an_offer_and_get_an_appointment(self):
        self._join()
        self._cancel_holder_appointment()
        entry = WaitlistEntry.objects.get()

        self.client.force_authenticate(self.waiter)
        response = self.client.post(f"/appointments/waitlist/{entry.id}/accept/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry.refresh_from_db()
        self.assertEqual(entry.status, WaitlistEntry.Status.BOOKED)
        self.assertEqual(entry.appointment.patient, self.waiter_patient)

    def test_offer_is_not_visible_to_an_unrelated_patient(self):
        self._join()
        self._cancel_holder_appointment()
        entry = WaitlistEntry.objects.get()

        intruder = User.objects.create_user(username="intruder")
        Patient.objects.create(user=intruder)
        self.client.force_authenticate(intruder)
        response = self.client.post(f"/appointments/waitlist/{entry.id}/accept/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accepting_a_refilled_slot_expires_the_offer(self):
        self._join()
        self._cancel_holder_appointment()
        entry = WaitlistEntry.objects.get()

        # Somebody books the place directly before the offer is accepted.
        other = User.objects.create_user(username="quick-booker")
        Appointment.objects.create(
            patient=Patient.objects.create(user=other),
            doctor=self.doctor,
            appointment_type=Appointment.Type.OFFLINE,
            symptoms="Straight in",
            scheduled_date=self.slot_date,
            time=self.slot,
        )

        self.client.force_authenticate(self.waiter)
        response = self.client.post(f"/appointments/waitlist/{entry.id}/accept/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        entry.refresh_from_db()
        self.assertEqual(entry.status, WaitlistEntry.Status.EXPIRED)
