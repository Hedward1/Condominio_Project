from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.http import Http404
from django.utils import timezone

from .models import Amenity, Reservation, ReservationStatus


def list_amenities_for_condominium(*, condominium):
    return Amenity.active_objects.filter(condominium=condominium).order_by("name")


def get_amenity_for_condominium(*, condominium, amenity_id):
    amenity = Amenity.active_objects.filter(id=amenity_id, condominium=condominium).first()
    if amenity is None:
        raise Http404("Area comum nao encontrada.")
    return amenity


def list_reservations_for_user(*, condominium, user):
    return (
        Reservation.active_objects.filter(condominium=condominium, requested_by=user)
        .select_related("amenity", "requested_by", "decided_by", "cancelled_by")
        .order_by("-start_at")
    )


def list_reservations_for_manager(*, condominium, filters=None):
    filters = filters or {}
    reservations = Reservation.active_objects.filter(condominium=condominium)
    if filters.get("status"):
        reservations = reservations.filter(status=filters["status"])
    if filters.get("amenity"):
        reservations = reservations.filter(amenity=filters["amenity"])
    return (
        reservations.select_related("amenity", "requested_by", "decided_by", "cancelled_by")
        .order_by("-start_at")
    )


def list_reservation_days_for_amenity(*, condominium, amenity, month_date):
    if amenity.condominium_id != condominium.id:
        raise Http404("Area comum nao encontrada.")

    current_timezone = timezone.get_current_timezone()
    month_start_date = date(month_date.year, month_date.month, 1)
    _, days_in_month = monthrange(month_start_date.year, month_start_date.month)
    month_end_date = (
        date(month_start_date.year + 1, 1, 1)
        if month_start_date.month == 12
        else date(month_start_date.year, month_start_date.month + 1, 1)
    )
    month_start = timezone.make_aware(
        datetime.combine(month_start_date, time.min),
        current_timezone,
    )
    month_end = timezone.make_aware(
        datetime.combine(month_end_date, time.min),
        current_timezone,
    )
    reservations = (
        Reservation.active_objects.filter(
            condominium=condominium,
            amenity=amenity,
            status__in=[ReservationStatus.APPROVED, ReservationStatus.PENDING],
            start_at__lt=month_end,
            end_at__gt=month_start,
        )
        .select_related("requested_by")
        .order_by("start_at")
    )

    reservations_by_day = {day: [] for day in range(1, days_in_month + 1)}
    for reservation in reservations:
        local_start = timezone.localtime(reservation.start_at, current_timezone)
        local_end = timezone.localtime(
            reservation.end_at - timedelta(microseconds=1),
            current_timezone,
        )
        first_day = max(local_start.date(), month_start_date)
        last_day = min(local_end.date(), month_end_date - timedelta(days=1))
        current_day = first_day
        while current_day <= last_day:
            reservations_by_day[current_day.day].append(
                {
                    "status": reservation.status,
                    "status_label": reservation.get_status_display(),
                    "time_range": (
                        f"{timezone.localtime(reservation.start_at, current_timezone):%H:%M} "
                        f"as {timezone.localtime(reservation.end_at, current_timezone):%H:%M}"
                    ),
                },
            )
            current_day += timedelta(days=1)

    days = []
    for day in range(1, days_in_month + 1):
        day_reservations = reservations_by_day[day]
        statuses = {reservation["status"] for reservation in day_reservations}
        if ReservationStatus.APPROVED in statuses:
            label = "Com reserva"
            badge_class = "danger"
        elif ReservationStatus.PENDING in statuses:
            label = "Pendente"
            badge_class = "warning"
        else:
            label = "Livre"
            badge_class = "success"
        days.append(
            {
                "date": date(month_start_date.year, month_start_date.month, day),
                "day": day,
                "label": label,
                "badge_class": badge_class,
                "reservations": day_reservations,
            },
        )
    return days


def get_reservation_for_user(*, condominium, user, reservation_id):
    reservation = (
        Reservation.active_objects.select_related(
            "amenity",
            "requested_by",
            "decided_by",
            "cancelled_by",
        )
        .filter(id=reservation_id, condominium=condominium, requested_by=user)
        .first()
    )
    if reservation is None:
        raise Http404("Reserva nao encontrada.")
    return reservation


def get_reservation_for_manager(*, condominium, reservation_id):
    reservation = (
        Reservation.active_objects.select_related(
            "amenity",
            "requested_by",
            "decided_by",
            "cancelled_by",
        )
        .filter(id=reservation_id, condominium=condominium)
        .first()
    )
    if reservation is None:
        raise Http404("Reserva nao encontrada.")
    return reservation
