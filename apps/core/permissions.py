from django.core.exceptions import PermissionDenied

from .models import CondominiumMembership, CondominiumRole

MANAGEMENT_ROLES = {
    CondominiumRole.CONDO_ADMIN,
    CondominiumRole.SYNDIC,
}

STAFF_ROLES = {
    CondominiumRole.CONDO_ADMIN,
    CondominiumRole.SYNDIC,
    CondominiumRole.COUNCIL,
    CondominiumRole.STAFF,
}

RESIDENT_ACCESS_ROLES = {
    CondominiumRole.RESIDENT,
    CondominiumRole.OWNER,
    CondominiumRole.TENANT,
    CondominiumRole.COUNCIL,
    CondominiumRole.STAFF,
    CondominiumRole.CONDO_ADMIN,
    CondominiumRole.SYNDIC,
}


def get_active_membership(user, condominium) -> CondominiumMembership | None:
    if user is None or not user.is_authenticated:
        return None
    return (
        CondominiumMembership.active_objects.filter(
            user=user,
            condominium=condominium,
            condominium__is_active=True,
        )
        .select_related("condominium", "user")
        .first()
    )


def require_active_membership(user, condominium) -> CondominiumMembership:
    membership = get_active_membership(user, condominium)
    if membership is None:
        raise PermissionDenied("Voce nao tem acesso a este condominio.")
    return membership


def user_has_condominium_access(user, condominium) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return condominium.is_active
    return get_active_membership(user, condominium) is not None


def user_can_manage_condominium(user, condominium) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return condominium.is_active
    membership = get_active_membership(user, condominium)
    return membership is not None and membership.role in MANAGEMENT_ROLES


def require_condominium_manager(user, condominium) -> CondominiumMembership | None:
    if user is not None and user.is_authenticated and user.is_superuser and condominium.is_active:
        return None

    membership = require_active_membership(user, condominium)
    if membership.role not in MANAGEMENT_ROLES:
        raise PermissionDenied("Voce nao tem permissao para gerenciar este condominio.")
    return membership
