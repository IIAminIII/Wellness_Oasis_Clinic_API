from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from operations.models import AuditEvent, Facility, RoleAssignment
from .models import Doctor, DoctorLeave


class DoctorLeaveTests(APITestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name="Main", code="main")
        self.doctor_user = User.objects.create_user(username="leave-doctor")
        self.doctor = Doctor.objects.create(user=self.doctor_user, fee=1000)
        self.admin = User.objects.create_user(username="leave-admin")
        RoleAssignment.objects.create(
            user=self.admin,
            role=RoleAssignment.Role.ADMINISTRATOR,
        )
        self.start = timezone.localdate() + timedelta(days=3)

    def _request_leave(self, as_user, doctor=None):
        self.client.force_authenticate(as_user)
        return self.client.post(
            "/doctors/leave/",
            {
                "doctor": (doctor or self.doctor).id,
                "start_date": str(self.start),
                "end_date": str(self.start + timedelta(days=2)),
                "reason": "Conference",
            },
            format="json",
        )

    def test_doctor_can_request_own_leave(self):
        response = self._request_leave(self.doctor_user)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        leave = DoctorLeave.objects.get()
        self.assertEqual(leave.status, DoctorLeave.Status.REQUESTED)

    def test_doctor_cannot_request_leave_for_a_colleague(self):
        other_user = User.objects.create_user(username="other-doctor")
        other = Doctor.objects.create(user=other_user, fee=1000)

        response = self._request_leave(self.doctor_user, doctor=other)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_end_before_start_is_rejected(self):
        self.client.force_authenticate(self.doctor_user)

        response = self.client.post(
            "/doctors/leave/",
            {
                "doctor": self.doctor.id,
                "start_date": str(self.start),
                "end_date": str(self.start - timedelta(days=1)),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administrator_approves_leave_and_it_is_audited(self):
        self._request_leave(self.doctor_user)
        leave = DoctorLeave.objects.get()
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/doctors/leave/{leave.id}/decide/",
            {"status": DoctorLeave.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        leave.refresh_from_db()
        self.assertEqual(leave.status, DoctorLeave.Status.APPROVED)
        self.assertEqual(leave.reviewed_by, self.admin)
        self.assertTrue(
            AuditEvent.objects.filter(action="doctor_leave.decided").exists()
        )

    def test_doctor_cannot_approve_their_own_leave(self):
        self._request_leave(self.doctor_user)
        leave = DoctorLeave.objects.get()

        response = self.client.post(
            f"/doctors/leave/{leave.id}/decide/",
            {"status": DoctorLeave.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_only_sees_their_own_leave(self):
        self._request_leave(self.doctor_user)
        other_user = User.objects.create_user(username="unrelated-doctor")
        other = Doctor.objects.create(user=other_user, fee=1000)
        DoctorLeave.objects.create(
            doctor=other,
            start_date=self.start,
            end_date=self.start,
        )
        self.client.force_authenticate(self.doctor_user)

        response = self.client.get("/doctors/leave/")

        self.assertEqual(response.data["count"], 1)
