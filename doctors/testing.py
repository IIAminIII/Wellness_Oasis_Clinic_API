"""Helpers for building valid slot/date pairs in tests.

Slots are now weekday-bound, so a test date can no longer be an arbitrary
``today + 1``; it has to fall on the slot's weekday.
"""

from datetime import date, time, timedelta

from django.utils import timezone

from .models import AvailableTime


def make_slot(*, weekday=0, start=time(9, 0), end=time(9, 30), capacity=1):
    return AvailableTime.objects.create(
        weekday=weekday,
        start_time=start,
        end_time=end,
        capacity=capacity,
    )


def next_date_for(slot, *, after: date | None = None) -> date:
    """The soonest future date that falls on ``slot``'s weekday."""
    cursor = (after or timezone.localdate()) + timedelta(days=1)
    while cursor.weekday() != slot.weekday:
        cursor += timedelta(days=1)
    return cursor
