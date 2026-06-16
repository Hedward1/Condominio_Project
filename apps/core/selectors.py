from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .models import Block, Condominium, CondominiumMembership, Unit, UnitOccupancy
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


def list_units_for_condominium(*, condominium):
    return (
        Unit.active_objects.filter(condominium=condominium)
        .select_related("block")
        .order_by("block__name", "number")
    )


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
        .select_related("unit", "user")
        .order_by("unit__number", "user__username")
    )


def get_membership_by_id_for_condominium(*, condominium, membership_id):
    membership = (
        CondominiumMembership.active_objects.select_related("user", "condominium")
        .filter(id=membership_id, condominium=condominium)
        .first()
    )
    if membership is None:
        raise Http404("Membro nao encontrado.")
    return membership


def get_occupancy_for_condominium(*, condominium, occupancy_id):
    occupancy = (
        UnitOccupancy.active_objects.select_related("unit", "user")
        .filter(id=occupancy_id, condominium=condominium)
        .first()
    )
    if occupancy is None:
        raise Http404("Morador por unidade nao encontrado.")
    return occupancy
