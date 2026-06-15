from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.audit.services import create_audit_log

from .middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from .models import (
    Block,
    Condominium,
    CondominiumMembership,
    CondominiumRole,
    CondominiumSettings,
    OccupancyType,
    Unit,
    UnitOccupancy,
)
from .permissions import require_condominium_manager
from .selectors import get_condominium_for_user

ASSIGNABLE_MEMBERSHIP_ROLES = {
    CondominiumRole.COUNCIL,
    CondominiumRole.STAFF,
    CondominiumRole.RESIDENT,
    CondominiumRole.OWNER,
    CondominiumRole.TENANT,
}


@transaction.atomic
def create_condominium(
    *,
    name: str,
    actor=None,
    slug: str | None = None,
    document_number: str = "",
    address: str = "",
    city: str = "",
    state: str = "",
    postal_code: str = "",
) -> Condominium:
    audit_actor = actor if getattr(actor, "is_authenticated", False) else None
    condominium = Condominium(
        name=name,
        slug=slug or slugify(name),
        document_number=document_number,
        address=address,
        city=city,
        state=state,
        postal_code=postal_code,
        created_by=audit_actor,
        updated_by=audit_actor,
    )
    condominium.full_clean()
    condominium.save()
    CondominiumSettings.objects.create(
        condominium=condominium,
        created_by=audit_actor,
        updated_by=audit_actor,
    )

    if audit_actor is not None:
        CondominiumMembership.objects.create(
            condominium=condominium,
            user=audit_actor,
            role=CondominiumRole.SYNDIC,
            invited_by=audit_actor,
            created_by=audit_actor,
            updated_by=audit_actor,
        )

    create_audit_log(
        condominium=condominium,
        actor=audit_actor,
        action="core.condominium.created",
        target=condominium,
    )
    return condominium


@transaction.atomic
def create_block(*, condominium: Condominium, actor, name: str, description: str = "") -> Block:
    require_condominium_manager(actor, condominium)
    block = Block(
        condominium=condominium,
        name=name,
        description=description,
        created_by=actor,
        updated_by=actor,
    )
    block.full_clean()
    block.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="core.block.created",
        target=block,
    )
    return block


@transaction.atomic
def create_unit(
    *,
    condominium: Condominium,
    actor,
    number: str,
    block: Block | None = None,
    floor: str = "",
    description: str = "",
) -> Unit:
    require_condominium_manager(actor, condominium)
    if block is not None and block.condominium_id != condominium.id:
        raise ValidationError({"block": "O bloco pertence a outro condominio."})

    unit = Unit(
        condominium=condominium,
        block=block,
        number=number,
        floor=floor,
        description=description,
        created_by=actor,
        updated_by=actor,
    )
    unit.full_clean()
    unit.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="core.unit.created",
        target=unit,
    )
    return unit


@transaction.atomic
def add_membership(
    *,
    condominium: Condominium,
    actor,
    user,
    role: CondominiumRole | str,
) -> CondominiumMembership:
    require_condominium_manager(actor, condominium)
    membership = CondominiumMembership(
        condominium=condominium,
        user=user,
        role=role,
        invited_by=actor,
        created_by=actor,
        updated_by=actor,
    )
    membership.full_clean()
    membership.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="core.membership.created",
        target=membership,
        metadata={"member_user_id": str(user.id), "role": str(role)},
    )
    return membership


@transaction.atomic
def create_user_membership(
    *,
    condominium: Condominium,
    actor,
    first_name: str,
    last_name: str = "",
    email: str,
    role: CondominiumRole | str,
    username: str = "",
    temporary_password: str = "",
) -> CondominiumMembership:
    require_condominium_manager(actor, condominium)
    if role not in ASSIGNABLE_MEMBERSHIP_ROLES:
        raise ValidationError({"role": "Este papel nao pode ser atribuido por esta tela."})

    User = get_user_model()
    normalized_email = email.strip().lower()
    user = User.objects.filter(email__iexact=normalized_email).first()

    if user is None:
        if not username:
            raise ValidationError({"username": "Informe um usuario para novo cadastro."})
        if not temporary_password:
            raise ValidationError({"temporary_password": "Informe uma senha temporaria."})

        user = User(
            username=username.strip(),
            email=normalized_email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        user.set_password(temporary_password)
        user.full_clean()
        user.save()
        create_audit_log(
            condominium=condominium,
            actor=actor,
            action="accounts.user.created",
            target=user,
            metadata={"created_for_condominium_id": str(condominium.id)},
        )
    elif not user.is_active:
        raise ValidationError({"email": "Este usuario esta inativo."})

    return add_membership(
        condominium=condominium,
        actor=actor,
        user=user,
        role=role,
    )


@transaction.atomic
def create_unit_occupancy(
    *,
    condominium: Condominium,
    actor,
    unit: Unit,
    user,
    occupancy_type: OccupancyType | str,
    is_primary: bool = False,
    starts_at=None,
    ends_at=None,
) -> UnitOccupancy:
    require_condominium_manager(actor, condominium)
    if unit.condominium_id != condominium.id:
        raise ValidationError({"unit": "A unidade pertence a outro condominio."})

    has_membership = CondominiumMembership.active_objects.filter(
        condominium=condominium,
        user=user,
    ).exists()
    if not has_membership:
        raise ValidationError({"user": "O usuario precisa ser membro ativo do condominio."})

    occupancy = UnitOccupancy(
        condominium=condominium,
        unit=unit,
        user=user,
        occupancy_type=occupancy_type,
        is_primary=is_primary,
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=actor,
        updated_by=actor,
    )
    occupancy.full_clean()
    occupancy.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="core.unit_occupancy.created",
        target=occupancy,
        metadata={"occupant_user_id": str(user.id), "unit_id": str(unit.id)},
    )
    return occupancy


def set_active_condominium_for_request(*, request, condominium_id) -> Condominium:
    condominium = get_condominium_for_user(user=request.user, condominium_id=condominium_id)
    request.session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    request.condominium = condominium
    create_audit_log(
        condominium=condominium,
        actor=request.user,
        action="core.condominium.selected",
        target=condominium,
        request=request,
    )
    return condominium
