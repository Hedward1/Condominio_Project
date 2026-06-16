from django.http import Http404

from .models import Amenity, Reservation


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


def list_reservations_for_manager(*, condominium):
    return (
        Reservation.active_objects.filter(condominium=condominium)
        .select_related("amenity", "requested_by", "decided_by", "cancelled_by")
        .order_by("-start_at")
    )


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
