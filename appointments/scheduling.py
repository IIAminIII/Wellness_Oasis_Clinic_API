"""Single source of truth for whether a slot can be booked.

Both the booking serializers and the public availability endpoint call these
helpers so a slot that the calendar shows as open is a slot the API accepts.
"""

from doctors.models import Weekday


def booked_count(*, doctor, slot, scheduled_date, exclude_pk=None):
    from .models import Appointment

    taken = Appointment.objects.filter(
        doctor=doctor,
        time=slot,
        scheduled_date=scheduled_date,
        cancel=False,
    )
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    return taken.count()


def remaining_capacity(*, doctor, slot, scheduled_date, exclude_pk=None):
    used = booked_count(
        doctor=doctor,
        slot=slot,
        scheduled_date=scheduled_date,
        exclude_pk=exclude_pk,
    )
    return max(slot.capacity - used, 0)


def offer_freed_slot(appointment):
    """Offer a slot that has just opened up to the longest-waiting patient.

    Returns the entry that was offered, or ``None`` when nobody is waiting.
    Offering is deliberately not the same as booking: the patient still has to
    accept, so a cancellation never silently creates an appointment for them.
    """
    from django.utils import timezone

    from .models import WaitlistEntry

    if remaining_capacity(
        doctor=appointment.doctor,
        slot=appointment.time,
        scheduled_date=appointment.scheduled_date,
    ) < 1:
        return None

    entry = (
        WaitlistEntry.objects.filter(
            doctor=appointment.doctor,
            time=appointment.time,
            requested_date=appointment.scheduled_date,
            status=WaitlistEntry.Status.WAITING,
        )
        .order_by("created_at")
        .first()
    )
    if entry is None:
        return None

    entry.status = WaitlistEntry.Status.OFFERED
    entry.offered_at = timezone.now()
    entry.save(update_fields=["status", "offered_at", "updated_at"])
    return entry


def slot_unavailable_reason(*, doctor, slot, scheduled_date, exclude_pk=None):
    """Return a human-readable reason, or ``None`` when the slot can be booked.

    Ordered cheapest-check-first so the common rejections avoid a query.
    """
    if not doctor.is_accepting_patients:
        return "This doctor is not accepting appointments."
    if not slot.is_active:
        return "This time slot is no longer offered."
    if slot.weekday != scheduled_date.weekday():
        return (
            f"This slot only runs on {Weekday(slot.weekday).label}, "
            f"but {scheduled_date:%Y-%m-%d} is a "
            f"{Weekday(scheduled_date.weekday()).label}."
        )
    if not doctor.available_time.filter(pk=slot.pk).exists():
        return "This time is not available for the selected doctor."
    if doctor.is_on_leave(scheduled_date):
        return "The doctor is on leave on that date."
    if not remaining_capacity(
        doctor=doctor,
        slot=slot,
        scheduled_date=scheduled_date,
        exclude_pk=exclude_pk,
    ):
        return "That appointment slot is fully booked."
    return None
