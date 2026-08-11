"""Set how many patients a doctor can see in a recurring slot.

Slots created before capacity existed default to 1, which reproduces the old
one-patient-per-slot behaviour. This command raises them in bulk rather than
clicking through the admin, and is safe to re-run.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from doctors.models import AvailableTime, Weekday


class Command(BaseCommand):
    help = "Set the patient capacity of recurring appointment slots."

    def add_arguments(self, parser):
        parser.add_argument(
            "capacity",
            type=int,
            help="Patients one doctor can see in the slot (1 or more).",
        )
        parser.add_argument(
            "--weekday",
            type=int,
            choices=[value for value, _ in Weekday.choices],
            help="Only slots on this weekday (0=Monday … 6=Sunday).",
        )
        parser.add_argument(
            "--slot",
            type=int,
            action="append",
            dest="slots",
            help="Only this slot id. Repeat for several.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Also change slots that are switched off.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        capacity = options["capacity"]
        if capacity < 1:
            raise CommandError("Capacity must be at least 1.")

        slots = AvailableTime.objects.all()
        if not options["include_inactive"]:
            slots = slots.filter(is_active=True)
        if options["weekday"] is not None:
            slots = slots.filter(weekday=options["weekday"])
        if options["slots"]:
            slots = slots.filter(pk__in=options["slots"])
            missing = set(options["slots"]) - set(slots.values_list("pk", flat=True))
            if missing:
                raise CommandError(
                    "No matching slot for id(s): "
                    + ", ".join(str(pk) for pk in sorted(missing))
                )

        slots = list(slots.order_by("weekday", "start_time"))
        if not slots:
            self.stdout.write(self.style.WARNING("No slots matched."))
            return

        changing = [slot for slot in slots if slot.capacity != capacity]
        for slot in slots:
            marker = "->" if slot.capacity != capacity else "  "
            self.stdout.write(
                f" {marker} {slot.name:<28} {slot.capacity} -> {capacity}"
                if slot.capacity != capacity
                else f" {marker} {slot.name:<28} {slot.capacity} (unchanged)"
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {len(changing)} of {len(slots)} slots would change."
                )
            )
            return

        # bulk_update skips save(), which is fine here: only capacity changes and
        # the generated name depends on weekday and times, not capacity.
        with transaction.atomic():
            for slot in changing:
                slot.capacity = capacity
            AvailableTime.objects.bulk_update(changing, ["capacity"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(changing)} of {len(slots)} slots to capacity {capacity}."
            )
        )
