from datetime import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from doctors.models import AvailableTime, Designation, Doctor, Specialization
from operations.models import Bed, Department, Facility, RoleAssignment, Room
from services.models import Service


SERVICES = [
    (
        "Diagnosis",
        "Clear diagnostic support to help clinicians identify conditions and plan the right care.",
        "services/image/diagnosis.jpg",
    ),
    (
        "Emergency Treatment",
        "Rapid assessment and stabilisation for urgent illnesses and injuries.",
        "services/image/Emergency_overview.jpg",
    ),
    (
        "Physical Therapy",
        "Individual rehabilitation plans that restore movement, function, and confidence.",
        "services/image/Physical-Therapy-and-Differential-Diagnosis.jpg",
    ),
    (
        "Surgery",
        "Coordinated surgical care from preparation through recovery and follow-up.",
        "services/image/What-Qualifies-as-Major-or-Minor-Surgery.jpg",
    ),
    (
        "Bone Care",
        "Assessment and treatment for fractures, joint problems, and bone health.",
        "services/image/bonestrtment.jpg",
    ),
    (
        "Hair Transplant",
        "Specialist consultation and personalised surgical hair-restoration planning.",
        "services/image/hairtransplant.jpeg",
    ),
]

# Which doctor specializations deliver each service. Drives the
# "doctors for this service" section on the public site.
SERVICE_SPECIALIZATIONS = {
    "Diagnosis": ["Neurology", "Ophthalmology"],
    "Emergency Treatment": ["Emergency Medicine", "General Surgery"],
    "Physical Therapy": ["Orthopedics"],
    "Surgery": ["General Surgery", "Orthopedics"],
    "Bone Care": ["Orthopedics"],
    "Hair Transplant": ["Dermatology", "General Surgery"],
}

DOCTORS = [
    {
        "username": "demo_doctor_alberto",
        "first_name": "Alberto",
        "last_name": "Ziesmer",
        "designation": "Medical Officer",
        "specialization": "Neurology",
        "fee": 1000,
        "image": "doctors/images/dovphtot.jpg",
    },
    {
        "username": "demo_doctor_caleb",
        "first_name": "Caleb",
        "last_name": "Cattaneo",
        "designation": "Consultant Surgeon",
        "specialization": "General Surgery",
        "fee": 1200,
        "image": "doctors/images/doc3.jpg",
    },
    {
        "username": "demo_doctor_holden",
        "first_name": "Holden",
        "last_name": "Cruce",
        "designation": "Consultant",
        "specialization": "Ophthalmology",
        "fee": 800,
        "image": "doctors/images/doc5.jpg",
    },
    {
        "username": "demo_doctor_mariana",
        "first_name": "Mariana",
        "last_name": "Holt",
        "designation": "Consultant",
        "specialization": "Orthopedics",
        "fee": 900,
        "image": "doctors/images/doc4.jpeg",
    },
    {
        "username": "demo_doctor_imran",
        "first_name": "Imran",
        "last_name": "Chowdhury",
        "designation": "Medical Officer",
        "specialization": "Emergency Medicine",
        "fee": 700,
        "image": "doctors/images/doc8.jpg",
    },
    {
        "username": "demo_doctor_sofia",
        "first_name": "Sofia",
        "last_name": "Renner",
        "designation": "Consultant",
        "specialization": "Dermatology",
        "fee": 1100,
        "image": "doctors/images/doc9.jpg",
    },
]

# (weekday, start, end, capacity) — weekday matches date.weekday().
TIMES = [
    (5, time(9, 0), time(12, 0), 4),
    (6, time(14, 0), time(17, 0), 4),
    (1, time(9, 0), time(12, 0), 3),
]

ROOMS = [
    ("101", "Consultation A", "consultation", 0),
    ("102", "Consultation B", "consultation", 0),
    ("201", "General ward", "ward", 6),
    ("301", "Intensive care", "icu", 3),
]


class Command(BaseCommand):
    help = "Create idempotent, non-patient demo catalogue data."

    def handle(self, *args, **options):
        facility, _ = Facility.objects.get_or_create(
            code="wellness-oasis-main",
            defaults={
                "name": "Wellness Oasis Main Hospital",
                "address": "Dhaka, Bangladesh",
                "phone": "+880 9600 000000",
            },
        )

        for name, description, image in SERVICES:
            service, _ = Service.objects.get_or_create(
                name=name,
                defaults={"description": description, "image": image},
            )
            changed = False
            if not service.description:
                service.description = description
                changed = True
            if not service.image:
                service.image = image
                changed = True
            if changed:
                service.save()
            for spec_name in SERVICE_SPECIALIZATIONS.get(name, []):
                specialization, _ = Specialization.objects.get_or_create(
                    name=spec_name,
                    defaults={"slug": slugify(spec_name)},
                )
                service.specializations.add(specialization)

        time_slots = [
            AvailableTime.objects.get_or_create(
                weekday=weekday,
                start_time=start,
                end_time=end,
                defaults={"capacity": capacity},
            )[0]
            for weekday, start, end, capacity in TIMES
        ]

        for item in DOCTORS:
            user, created = User.objects.get_or_create(
                username=item["username"],
                defaults={
                    "first_name": item["first_name"],
                    "last_name": item["last_name"],
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            designation, _ = Designation.objects.get_or_create(
                name=item["designation"],
                defaults={"slug": slugify(item["designation"])},
            )
            specialization, _ = Specialization.objects.get_or_create(
                name=item["specialization"],
                defaults={"slug": slugify(item["specialization"])},
            )
            department, _ = Department.objects.get_or_create(
                facility=facility,
                code=slugify(item["specialization"]),
                defaults={"name": item["specialization"]},
            )
            doctor, _ = Doctor.objects.get_or_create(
                user=user,
                defaults={
                    "fee": item["fee"],
                    "image": item["image"],
                    "bio": (
                        "Focused on clear communication, evidence-based care, "
                        "and practical treatment plans."
                    ),
                },
            )
            doctor.designation.add(designation)
            doctor.specialization.add(specialization)
            doctor.available_time.add(*time_slots)
            RoleAssignment.objects.update_or_create(
                user=user,
                role=RoleAssignment.Role.DOCTOR,
                facility=facility,
                defaults={
                    "department": department,
                    "is_active": True,
                },
            )

        for number, name, kind, bed_count in ROOMS:
            room, _ = Room.objects.get_or_create(
                facility=facility,
                number=number,
                defaults={"name": name, "kind": kind},
            )
            for index in range(bed_count):
                Bed.objects.get_or_create(room=room, label=f"{number}-{index + 1}")

        self.stdout.write(self.style.SUCCESS("Demo catalogue is ready."))
