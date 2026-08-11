from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AuditEvent, Bed, Department, Facility, RoleAssignment, Room


class WardInventoryTests(APITestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name="Main", code="main")
        self.department = Department.objects.create(
            facility=self.facility,
            name="Cardiology",
            code="cardiology",
        )
        self.admin = User.objects.create_user(username="ward-admin")
        RoleAssignment.objects.create(
            user=self.admin,
            role=RoleAssignment.Role.ADMINISTRATOR,
        )
        self.nurse = User.objects.create_user(username="ward-nurse")
        RoleAssignment.objects.create(
            user=self.nurse,
            role=RoleAssignment.Role.NURSE,
            facility=self.facility,
        )
        self.room = Room.objects.create(
            facility=self.facility,
            department=self.department,
            number="201",
            kind=Room.Kind.WARD,
        )
        self.bed = Bed.objects.create(room=self.room, label="201-1")

    def test_administrator_can_create_a_room(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/operations/rooms/",
            {
                "facility": self.facility.id,
                "department": self.department.id,
                "number": "202",
                "kind": Room.Kind.WARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_nurse_cannot_create_a_room(self):
        self.client.force_authenticate(self.nurse)

        response = self.client.post(
            "/operations/rooms/",
            {
                "facility": self.facility.id,
                "number": "203",
                "kind": Room.Kind.WARD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_room_rejects_a_department_from_another_facility(self):
        other_facility = Facility.objects.create(name="Annexe", code="annexe")
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/operations/rooms/",
            {
                "facility": other_facility.id,
                "department": self.department.id,
                "number": "301",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data["errors"])

    def test_nurse_can_change_bed_status_and_it_is_audited(self):
        self.client.force_authenticate(self.nurse)

        response = self.client.patch(
            f"/operations/beds/{self.bed.id}/",
            {"status": Bed.Status.OCCUPIED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, Bed.Status.OCCUPIED)
        self.assertTrue(
            AuditEvent.objects.filter(action="bed.status_changed").exists()
        )

    def test_room_reports_available_bed_count(self):
        Bed.objects.create(
            room=self.room,
            label="201-2",
            status=Bed.Status.OCCUPIED,
        )
        self.client.force_authenticate(self.nurse)

        response = self.client.get(f"/operations/rooms/{self.room.id}/")

        self.assertEqual(response.data["available_beds"], 1)
        self.assertEqual(len(response.data["beds"]), 2)
