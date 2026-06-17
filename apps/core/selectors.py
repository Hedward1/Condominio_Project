from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.http import Http404

from .models import (
    Block,
    Condominium,
    CondominiumMembership,
    OccupancyType,
    Unit,
    UnitOccupancy,
)
from .permissions import user_has_condominium_access


def list_condominiums_for_user(user):
    if user is None or not user.is_authenticated:
        return Condominium.objects.none()
    if user.is_superuser:
        return Condominium.active_objects.all()
    return (
        Condominium.active_objects.filter(
            memberships__user=user,
            memberships__is_active=True,
        )
        .distinct()
        .order_by("name")
    )


def get_condominium_for_user(*, user, condominium_id):
    condominium = Condominium.active_objects.filter(id=condominium_id).first()
    if condominium is None or not user_has_condominium_access(user, condominium):
        raise PermissionDenied("Voce nao tem acesso a este condominio.")
    return condominium


def get_membership_for_condominium(*, condominium, user):
    return (
        CondominiumMembership.active_objects.select_related("condominium", "user")
        .filter(condominium=condominium, user=user)
        .first()
    )


def list_memberships_for_condominium(*, condominium):
    return (
        CondominiumMembership.active_objects.filter(condominium=condominium)
        .select_related("user")
        .order_by("user__username")
    )


def list_membership_users_for_condominium(*, condominium):
    User = get_user_model()
    return (
        User.objects.filter(
            condominium_memberships__condominium=condominium,
            condominium_memberships__is_active=True,
            is_active=True,
        )
        .distinct()
        .order_by("first_name", "last_name", "username")
    )


def list_blocks_for_condominium(*, condominium):
    return Block.active_objects.filter(condominium=condominium).order_by("name")


def get_block_for_condominium(*, condominium, block_id):
    block = Block.active_objects.filter(id=block_id, condominium=condominium).first()
    if block is None:
        raise Http404("Bloco nao encontrado.")
    return block


def list_units_for_condominium(*, condominium, filters=None):
    filters = filters or {}
    owner_occupancies = (
        UnitOccupancy.active_objects.filter(
            condominium=condominium,
            occupancy_type=OccupancyType.OWNER,
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__username")
    )
    resident_occupancies = (
        UnitOccupancy.active_objects.filter(
            condominium=condominium,
            occupancy_type__in=[OccupancyType.RESIDENT, OccupancyType.TENANT],
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__username")
    )
    active_owner_exists = UnitOccupancy.active_objects.filter(
        condominium=condominium,
        unit=OuterRef("pk"),
        occupancy_type=OccupancyType.OWNER,
    )
    active_resident_exists = UnitOccupancy.active_objects.filter(
        condominium=condominium,
        unit=OuterRef("pk"),
        occupancy_type__in=[OccupancyType.RESIDENT, OccupancyType.TENANT],
    )
    queryset = (
        Unit.active_objects.filter(condominium=condominium)
        .select_related("block")
        .annotate(
            has_active_owner=Exists(active_owner_exists),
            has_active_resident=Exists(active_resident_exists),
        )
        .prefetch_related(
            Prefetch(
                "occupancies",
                queryset=owner_occupancies,
                to_attr="active_owner_occupancies",
            ),
            Prefetch(
                "occupancies",
                queryset=resident_occupancies,
                to_attr="active_resident_occupancies",
            ),
        )
    )
    number = filters.get("number")
    if number:
        queryset = queryset.filter(number__icontains=number)
    block = filters.get("block")
    if block is not None:
        queryset = queryset.filter(block=block)
    situation = filters.get("situation")
    if situation == "missing_owner":
        queryset = queryset.filter(has_active_owner=False)
    elif situation == "missing_resident":
        queryset = queryset.filter(has_active_resident=False)
    elif situation == "complete":
        queryset = queryset.filter(has_active_owner=True, has_active_resident=True)
    elif situation == "incomplete":
        queryset = queryset.filter(Q(has_active_owner=False) | Q(has_active_resident=False))

    return queryset.order_by("block__name", "number")


def get_unit_for_condominium(*, condominium, unit_id):
    unit = (
        Unit.active_objects.select_related("block")
        .filter(id=unit_id, condominium=condominium)
        .first()
    )
    if unit is None:
        raise Http404("Unidade nao encontrada.")
    return unit


def list_occupancies_for_condominium(*, condominium):
    return (
        UnitOccupancy.active_objects.filter(condominium=condominium)
        .select_related("unit", "unit__block", "user")
        .order_by("unit__number", "user__username")
    )


def list_occupancies_for_unit(*, condominium, unit):
    return (
        UnitOccupancy.active_objects.filter(condominium=condominium, unit=unit)
        .select_related("unit", "unit__block", "user")
        .order_by("occupancy_type", "user__first_name", "user__last_name", "user__username")
    )


def get_membership_by_id_for_condominium(*, condominium, membership_id):
    membership = (
        CondominiumMembership.active_objects.select_related("user", "condominium")
        .filter(id=membership_id, condominium=condominium)
        .first()
    )
    if membership is None:
        raise Http404("Pessoa nao encontrada.")
    return membership


def get_occupancy_for_condominium(*, condominium, occupancy_id):
    occupancy = (
        UnitOccupancy.active_objects.select_related("unit", "user")
        .filter(id=occupancy_id, condominium=condominium)
        .first()
    )
    if occupancy is None:
        raise Http404("Vinculo por unidade nao encontrado.")
    return occupancy
