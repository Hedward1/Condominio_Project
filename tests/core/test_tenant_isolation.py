import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.core.models import Block, Condominium, CondominiumMembership, CondominiumRole
from apps.core.selectors import get_condominium_for_user, list_condominiums_for_user
from apps.core.services import create_unit


@pytest.fixture
def condominiums(db):
    first = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    second = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    return first, second


@pytest.mark.django_db
def test_user_lists_only_linked_condominiums(user_factory, condominiums):
    user = user_factory(username="resident")
    condo_a, condo_b = condominiums
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=user,
        role=CondominiumRole.RESIDENT,
    )

    results = list(list_condominiums_for_user(user))

    assert condo_a in results
    assert condo_b not in results


@pytest.mark.django_db
def test_get_condominium_for_user_blocks_cross_tenant_access(user_factory, condominiums):
    user = user_factory(username="resident")
    condo_a, condo_b = condominiums
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=user,
        role=CondominiumRole.RESIDENT,
    )

    with pytest.raises(PermissionDenied):
        get_condominium_for_user(user=user, condominium_id=condo_b.id)


@pytest.mark.django_db
def test_create_unit_rejects_block_from_other_condominium(user_factory, condominiums):
    syndic = user_factory(username="syndic")
    condo_a, condo_b = condominiums
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=syndic,
        role=CondominiumRole.SYNDIC,
    )
    other_block = Block.objects.create(condominium=condo_b, name="B")

    with pytest.raises(ValidationError):
        create_unit(
            condominium=condo_a,
            actor=syndic,
            block=other_block,
            number="101",
        )


@pytest.mark.django_db
def test_create_unit_scopes_to_condominium_and_creates_audit_log(user_factory, condominiums):
    syndic = user_factory(username="syndic")
    condo_a, _ = condominiums
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=syndic,
        role=CondominiumRole.SYNDIC,
    )

    unit = create_unit(
        condominium=condo_a,
        actor=syndic,
        number="101",
    )

    assert unit.condominium == condo_a
    assert AuditLog.objects.filter(
        condominium=condo_a,
        actor=syndic,
        action="core.unit.created",
        object_id=str(unit.id),
    ).exists()
