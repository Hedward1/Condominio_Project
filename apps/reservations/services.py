from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import create_audit_log
from apps.core.permissions import (
    require_active_membership,
    require_condominium_manager,
    user_can_manage_condominium,
)

from .models import Amenity, Reservation, ReservationStatus

OPEN_RESERVATION_STATUSES = {
    ReservationStatus.PENDING,
    ReservationStatus.APPROVED,
}


def _validate_amenity_condominium(*, condominium, amenity: Amenity | None):
    if amenity is not None and amenity.condominium_id != condominium.id:
        raise ValidationError({"amenity": "A area comum pertence a outro condominio."})
    if amenity is not None and not amenity.is_active:
        raise ValidationError({"amenity": "A area comum esta inativa."})


def _validate_reservation_condominium(*, condominium, reservation: Reservation):
    if reservation.condominium_id != condominium.id:
        raise ValidationError({"reservation": "A reserva pertence a outro condominio."})


def _validate_unique_active_amenity_name(
    *,
    condominium,
    name: str,
    amenity: Amenity | None = None,
):
    duplicate_query = Amenity.active_objects.filter(
        condominium=condominium,
        name__iexact=name.strip(),
    )
    if amenity is not None:
        duplicate_query = duplicate_query.exclude(id=amenity.id)
    if duplicate_query.exists():
        raise ValidationError({"name": "Ja existe uma area comum ativa com este nome."})


def _validate_reservation_times(*, start_at, end_at):
    if end_at <= start_at:
        raise ValidationError({"end_at": "A data final deve ser maior que a inicial."})
    if start_at < timezone.now():
        raise ValidationError({"start_at": "Nao e possivel reservar uma data no passado."})


def _approved_overlap_exists(
    *,
    condominium,
    amenity: Amenity,
    start_at,
    end_at,
    reservation: Reservation | None = None,
) -> bool:
    overlaps = Reservation.active_objects.filter(
        condominium=condominium,
        amenity=amenity,
        status=ReservationStatus.APPROVED,
        start_at__lt=end_at,
        end_at__gt=start_at,
    )
    if reservation is not None:
        overlaps = overlaps.exclude(id=reservation.id)
    return overlaps.exists()


def _validate_no_approved_overlap(
    *,
    condominium,
    amenity: Amenity,
    start_at,
    end_at,
    reservation: Reservation | None = None,
):
    if _approved_overlap_exists(
        condominium=condominium,
        amenity=amenity,
        start_at=start_at,
        end_at=end_at,
        reservation=reservation,
    ):
        raise ValidationError(
            {"reservation": "Ja existe uma reserva aprovada para este periodo."},
        )


@transaction.atomic
def create_amenity(*, condominium, actor, name: str, description: str = "", rules: str = ""):
    require_condominium_manager(actor, condominium)
    _validate_unique_active_amenity_name(condominium=condominium, name=name)

    amenity = Amenity(
        condominium=condominium,
        name=name.strip(),
        description=description,
        rules=rules,
        created_by=actor,
        updated_by=actor,
    )
    amenity.full_clean()
    amenity.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.amenity.created",
        target=amenity,
    )
    return amenity


@transaction.atomic
def update_amenity(
    *,
    condominium,
    actor,
    amenity: Amenity,
    name: str,
    description: str = "",
    rules: str = "",
):
    require_condominium_manager(actor, condominium)
    _validate_amenity_condominium(condominium=condominium, amenity=amenity)
    _validate_unique_active_amenity_name(
        condominium=condominium,
        name=name,
        amenity=amenity,
    )

    changes = {
        "name": {"from": amenity.name, "to": name.strip()},
        "description": {"from": amenity.description, "to": description},
        "rules": {"from": amenity.rules, "to": rules},
    }
    amenity.name = name.strip()
    amenity.description = description
    amenity.rules = rules
    amenity.updated_by = actor
    amenity.full_clean()
    amenity.save(update_fields=["name", "description", "rules", "updated_by", "updated_at"])
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.amenity.updated",
        target=amenity,
        changes=changes,
    )
    return amenity


@transaction.atomic
def deactivate_amenity(*, condominium, actor, amenity: Amenity):
    require_condominium_manager(actor, condominium)
    _validate_amenity_condominium(condominium=condominium, amenity=amenity)
    if Reservation.active_objects.filter(
        condominium=condominium,
        amenity=amenity,
        status__in=OPEN_RESERVATION_STATUSES,
    ).exists():
        raise ValidationError(
            {
                "amenity": (
                    "Esta area comum possui reservas pendentes ou aprovadas. "
                    "Finalize ou cancele as reservas primeiro."
                ),
            },
        )

    amenity.soft_delete(user=actor)
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.amenity.deactivated",
        target=amenity,
    )
    return amenity


@transaction.atomic
def request_reservation(
    *,
    condominium,
    actor,
    amenity: Amenity,
    start_at,
    end_at,
    notes: str = "",
):
    require_active_membership(actor, condominium)
    _validate_amenity_condominium(condominium=condominium, amenity=amenity)
    _validate_reservation_times(start_at=start_at, end_at=end_at)
    _validate_no_approved_overlap(
        condominium=condominium,
        amenity=amenity,
        start_at=start_at,
        end_at=end_at,
    )

    reservation = Reservation(
        condominium=condominium,
        amenity=amenity,
        requested_by=actor,
        start_at=start_at,
        end_at=end_at,
        notes=notes,
        status=ReservationStatus.PENDING,
        created_by=actor,
        updated_by=actor,
    )
    reservation.full_clean()
    reservation.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.reservation.requested",
        target=reservation,
    )
    return reservation


@transaction.atomic
def approve_reservation(*, condominium, actor, reservation: Reservation, manager_notes: str = ""):
    require_condominium_manager(actor, condominium)
    _validate_reservation_condominium(condominium=condominium, reservation=reservation)
    if reservation.status != ReservationStatus.PENDING:
        raise ValidationError({"reservation": "Somente reservas pendentes podem ser aprovadas."})
    _validate_no_approved_overlap(
        condominium=condominium,
        amenity=reservation.amenity,
        start_at=reservation.start_at,
        end_at=reservation.end_at,
        reservation=reservation,
    )

    old_status = reservation.status
    reservation.status = ReservationStatus.APPROVED
    reservation.manager_notes = manager_notes
    reservation.decided_by = actor
    reservation.decided_at = timezone.now()
    reservation.updated_by = actor
    reservation.full_clean()
    reservation.save(
        update_fields=[
            "status",
            "manager_notes",
            "decided_by",
            "decided_at",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.reservation.approved",
        target=reservation,
        changes={"status": {"from": old_status, "to": reservation.status}},
    )
    return reservation


@transaction.atomic
def reject_reservation(*, condominium, actor, reservation: Reservation, manager_notes: str = ""):
    require_condominium_manager(actor, condominium)
    _validate_reservation_condominium(condominium=condominium, reservation=reservation)
    if reservation.status != ReservationStatus.PENDING:
        raise ValidationError({"reservation": "Somente reservas pendentes podem ser rejeitadas."})

    old_status = reservation.status
    reservation.status = ReservationStatus.REJECTED
    reservation.manager_notes = manager_notes
    reservation.decided_by = actor
    reservation.decided_at = timezone.now()
    reservation.updated_by = actor
    reservation.full_clean()
    reservation.save(
        update_fields=[
            "status",
            "manager_notes",
            "decided_by",
            "decided_at",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.reservation.rejected",
        target=reservation,
        changes={"status": {"from": old_status, "to": reservation.status}},
    )
    return reservation


@transaction.atomic
def cancel_reservation(*, condominium, actor, reservation: Reservation, manager_notes: str = ""):
    if not user_can_manage_condominium(actor, condominium):
        raise PermissionDenied("Voce nao tem permissao para cancelar reservas.")
    _validate_reservation_condominium(condominium=condominium, reservation=reservation)
    if reservation.status not in OPEN_RESERVATION_STATUSES:
        raise ValidationError({"reservation": "Somente reservas pendentes ou aprovadas podem ser canceladas."})

    old_status = reservation.status
    reservation.status = ReservationStatus.CANCELLED
    reservation.manager_notes = manager_notes
    reservation.cancelled_by = actor
    reservation.cancelled_at = timezone.now()
    reservation.updated_by = actor
    reservation.full_clean()
    reservation.save(
        update_fields=[
            "status",
            "manager_notes",
            "cancelled_by",
            "cancelled_at",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="reservations.reservation.cancelled",
        target=reservation,
        changes={"status": {"from": old_status, "to": reservation.status}},
    )
    return reservation
