import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Block, Condominium, CondominiumMembership, CondominiumRole, Unit


def activate_condominium(client, condominium):
    session = client.session
    session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    session.save()


@pytest.fixture
def core_context(db, user_factory):
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    syndic = user_factory(username="syndic", password="testpass123")
    resident = user_factory(username="resident", password="testpass123")
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=syndic,
        role=CondominiumRole.SYNDIC,
    )
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=resident,
        role=CondominiumRole.RESIDENT,
    )
    return {
        "condo_a": condo_a,
        "condo_b": condo_b,
        "syndic": syndic,
        "resident": resident,
    }


@pytest.mark.django_db
def test_resident_cannot_access_core_management(client, core_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:block_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_block_list_shows_only_active_condominium_blocks(client, core_context):
    Block.objects.create(condominium=core_context["condo_a"], name="Torre A")
    Block.objects.create(condominium=core_context["condo_b"], name="Torre B")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:block_list"))

    assert response.status_code == 200
    assert b"Torre A" in response.content
    assert b"Torre B" not in response.content


@pytest.mark.django_db
def test_syndic_creates_block_with_audit_log(client, core_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:block_create"),
        {"name": "Torre A", "description": "Bloco principal"},
    )

    assert response.status_code == 302
    block = Block.objects.get(condominium=core_context["condo_a"], name="Torre A")
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.block.created",
        object_id=str(block.id),
    ).exists()


@pytest.mark.django_db
def test_unit_create_rejects_block_from_other_condominium(client, core_context):
    other_block = Block.objects.create(condominium=core_context["condo_b"], name="Torre B")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_create"),
        {"block": str(other_block.id), "number": "101", "floor": "1"},
    )

    assert response.status_code == 200
    assert not Unit.objects.filter(condominium=core_context["condo_a"], number="101").exists()


@pytest.mark.django_db
def test_membership_create_creates_user_in_active_condominium(client, core_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:membership_create"),
        {
            "first_name": "Maria",
            "last_name": "Silva",
            "email": "maria@example.com",
            "username": "maria",
            "temporary_password": "testpass123",
            "role": CondominiumRole.RESIDENT,
        },
    )

    assert response.status_code == 302
    user = get_user_model().objects.get(email="maria@example.com")
    membership = CondominiumMembership.objects.get(
        condominium=core_context["condo_a"],
        user=user,
    )
    assert membership.role == CondominiumRole.RESIDENT
    assert not CondominiumMembership.objects.filter(
        condominium=core_context["condo_b"],
        user=user,
    ).exists()
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.membership.created",
        object_id=str(membership.id),
    ).exists()


@pytest.mark.django_db
def test_membership_create_does_not_allow_manager_role_from_form(client, core_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:membership_create"),
        {
            "first_name": "Outro",
            "last_name": "Sindico",
            "email": "outro@example.com",
            "username": "outro",
            "temporary_password": "testpass123",
            "role": CondominiumRole.SYNDIC,
        },
    )

    assert response.status_code == 200
    assert not CondominiumMembership.objects.filter(
        condominium=core_context["condo_a"],
        user__email="outro@example.com",
    ).exists()
