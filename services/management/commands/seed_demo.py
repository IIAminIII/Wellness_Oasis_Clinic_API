from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from doctors.models import AvailableTime, Designation, Doctor, Specialization
from operations.models import Department, Facility, RoleAssignment
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
]

TIMES = [
    "Saturday 09:00 - 12:00",
    "Sunday 14:00 - 17:00",
    "Tuesday 09:00 - 12:00",
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

        time_slots = [
            AvailableTime.objects.get_or_create(name=name)[0] for name in TIMES
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

        self.stdout.write(self.style.SUCCESS("Demo catalogue is ready."))
