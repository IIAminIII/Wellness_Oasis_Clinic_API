from datetime import time
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from .models import AvailableTime
from .testing import make_slot


class SetSlotCapacityCommandTests(TestCase):
    def setUp(self):
        self.monday = make_slot(weekday=0, start=time(9, 0), end=time(12, 0))
        self.tuesday = make_slot(weekday=1, start=time(9, 0), end=time(12, 0))
        self.retired = make_slot(weekday=2, start=time(9, 0), end=time(12, 0))
        AvailableTime.objects.filter(pk=self.retired.pk).update(is_active=False)

    def _run(self, *args):
        out = StringIO()
        call_command("set_slot_capacity", *args, stdout=out)
        return out.getvalue()

    def test_sets_capacity_on_every_active_slot(self):
        self._run("4")

        self.monday.refresh_from_db()
        self.tuesday.refresh_from_db()
        self.assertEqual(self.monday.capacity, 4)
        self.assertEqual(self.tuesday.capacity, 4)

    def test_inactive_slots_are_left_alone_by_default(self):
        self._run("4")

        self.retired.refresh_from_db()
        self.assertEqual(self.retired.capacity, 1)

    def test_include_inactive_covers_retired_slots(self):
        self._run("4", "--include-inactive")

        self.retired.refresh_from_db()
        self.assertEqual(self.retired.capacity, 4)

    def test_weekday_filter_limits_the_change(self):
        self._run("6", "--weekday", "1")

        self.monday.refresh_from_db()
        self.tuesday.refresh_from_db()
        self.assertEqual(self.monday.capacity, 1)
        self.assertEqual(self.tuesday.capacity, 6)

    def test_slot_filter_limits_the_change(self):
        self._run("5", "--slot", str(self.monday.pk))

        self.monday.refresh_from_db()
        self.tuesday.refresh_from_db()
        self.assertEqual(self.monday.capacity, 5)
        self.assertEqual(self.tuesday.capacity, 1)

    def test_dry_run_writes_nothing(self):
        output = self._run("9", "--dry-run")

        self.monday.refresh_from_db()
        self.assertEqual(self.monday.capacity, 1)
        self.assertIn("would change", output)

    def test_capacity_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self._run("0")

    def test_unknown_slot_id_is_refused(self):
        with self.assertRaises(CommandError):
            self._run("4", "--slot", "9999")

    def test_rerunning_is_a_no_op(self):
        self._run("4")

        output = self._run("4")

        self.assertIn("Updated 0 of 2 slots", output)

    def test_slot_labels_survive_the_update(self):
        self._run("4")

        self.monday.refresh_from_db()
        self.assertEqual(self.monday.name, "Monday 09:00 - 12:00")
