import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import (
    Block,
    Condominium,
    CondominiumMembership,
    CondominiumRole,
    OccupancyType,
    Unit,
    UnitOccupancy,
)


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
    assert "Você não tem permissão para acessar esta área.".encode() in response.content


@pytest.mark.django_db
def test_resident_cannot_access_unit_occupancy_management(client, core_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:unit_occupancy_list"))

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
def test_syndic_updates_block_with_audit_log(client, core_context):
    block = Block.objects.create(condominium=core_context["condo_a"], name="Torre A")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:block_update", args=[block.id]),
        {"name": "Torre Alpha", "description": "Atualizado"},
    )

    assert response.status_code == 302
    block.refresh_from_db()
    assert block.name == "Torre Alpha"
    assert block.description == "Atualizado"
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.block.updated",
        object_id=str(block.id),
    ).exists()


@pytest.mark.django_db
def test_block_update_blocks_cross_tenant_access(client, core_context):
    other_block = Block.objects.create(condominium=core_context["condo_b"], name="Torre B")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:block_update", args=[other_block.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_syndic_deactivates_block_with_audit_log(client, core_context):
    block = Block.objects.create(condominium=core_context["condo_a"], name="Torre A")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:block_deactivate", args=[block.id]))

    assert response.status_code == 302
    block.refresh_from_db()
    assert block.is_active is False
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.block.deactivated",
        object_id=str(block.id),
    ).exists()


@pytest.mark.django_db
def test_block_deactivate_blocks_cross_tenant_access(client, core_context):
    other_block = Block.objects.create(condominium=core_context["condo_b"], name="Torre B")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:block_deactivate", args=[other_block.id]))

    assert response.status_code == 404
    other_block.refresh_from_db()
    assert other_block.is_active is True


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
def test_syndic_updates_unit_with_audit_log(client, core_context):
    block = Block.objects.create(condominium=core_context["condo_a"], name="Torre A")
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_update", args=[unit.id]),
        {
            "block": str(block.id),
            "number": "102",
            "floor": "1",
            "description": "Atualizada",
        },
    )

    assert response.status_code == 302
    unit.refresh_from_db()
    assert unit.block == block
    assert unit.number == "102"
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.unit.updated",
        object_id=str(unit.id),
    ).exists()


@pytest.mark.django_db
def test_unit_update_rejects_block_from_other_condominium(client, core_context):
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    other_block = Block.objects.create(condominium=core_context["condo_b"], name="Torre B")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_update", args=[unit.id]),
        {
            "block": str(other_block.id),
            "number": "102",
            "floor": "1",
            "description": "Nao deve salvar",
        },
    )

    assert response.status_code == 200
    unit.refresh_from_db()
    assert unit.number == "101"
    assert unit.block_id is None


@pytest.mark.django_db
def test_unit_update_blocks_cross_tenant_access(client, core_context):
    other_unit = Unit.objects.create(condominium=core_context["condo_b"], number="202")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:unit_update", args=[other_unit.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_syndic_deactivates_unit_with_audit_log(client, core_context):
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:unit_deactivate", args=[unit.id]))

    assert response.status_code == 302
    unit.refresh_from_db()
    assert unit.is_active is False
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.unit.deactivated",
        object_id=str(unit.id),
    ).exists()


@pytest.mark.django_db
def test_unit_deactivate_blocks_cross_tenant_access(client, core_context):
    other_unit = Unit.objects.create(condominium=core_context["condo_b"], number="202")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:unit_deactivate", args=[other_unit.id]))

    assert response.status_code == 404
    other_unit.refresh_from_db()
    assert other_unit.is_active is True


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


@pytest.mark.django_db
def test_syndic_deactivates_membership_with_audit_log(client, core_context):
    membership = CondominiumMembership.objects.get(
        condominium=core_context["condo_a"],
        user=core_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:membership_deactivate", args=[membership.id]))

    assert response.status_code == 302
    membership.refresh_from_db()
    assert membership.is_active is False
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.membership.deactivated",
        object_id=str(membership.id),
    ).exists()


@pytest.mark.django_db
def test_membership_deactivate_blocks_cross_tenant_access(client, core_context, user_factory):
    other_user = user_factory(username="other", email="other@example.com")
    other_membership = CondominiumMembership.objects.create(
        condominium=core_context["condo_b"],
        user=other_user,
        role=CondominiumRole.RESIDENT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:membership_deactivate", args=[other_membership.id]))

    assert response.status_code == 404
    other_membership.refresh_from_db()
    assert other_membership.is_active is True


@pytest.mark.django_db
def test_membership_deactivate_blocks_last_active_manager(client, core_context):
    manager_membership = CondominiumMembership.objects.get(
        condominium=core_context["condo_a"],
        user=core_context["syndic"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:membership_deactivate", args=[manager_membership.id]))

    assert response.status_code == 200
    manager_membership.refresh_from_db()
    assert manager_membership.is_active is True


@pytest.mark.django_db
def test_unit_occupancy_list_shows_only_active_condominium(client, core_context, user_factory):
    other_user = user_factory(username="other", email="other@example.com")
    unit_a = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    unit_b = Unit.objects.create(condominium=core_context["condo_b"], number="202")
    CondominiumMembership.objects.create(
        condominium=core_context["condo_b"],
        user=other_user,
        role=CondominiumRole.RESIDENT,
    )
    UnitOccupancy.objects.create(
        condominium=core_context["condo_a"],
        unit=unit_a,
        user=core_context["resident"],
        occupancy_type=OccupancyType.RESIDENT,
    )
    UnitOccupancy.objects.create(
        condominium=core_context["condo_b"],
        unit=unit_b,
        user=other_user,
        occupancy_type=OccupancyType.RESIDENT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:unit_occupancy_list"))

    assert response.status_code == 200
    assert b"101" in response.content
    assert b"202" not in response.content
    assert b"other@example.com" not in response.content


@pytest.mark.django_db
def test_unit_occupancy_form_renders_only_active_condominium_choices(
    client,
    core_context,
    user_factory,
):
    Unit.objects.create(condominium=core_context["condo_a"], number="101")
    Unit.objects.create(condominium=core_context["condo_b"], number="202")
    other_user = user_factory(username="other", email="other@example.com")
    user_factory(username="outsider", email="outsider@example.com")
    inactive_member = user_factory(username="inactive_member", email="inactive@example.com")
    CondominiumMembership.objects.create(
        condominium=core_context["condo_b"],
        user=other_user,
        role=CondominiumRole.RESIDENT,
    )
    CondominiumMembership.objects.create(
        condominium=core_context["condo_a"],
        user=inactive_member,
        role=CondominiumRole.RESIDENT,
        is_active=False,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.get(reverse("core:unit_occupancy_create"))

    assert response.status_code == 200
    assert b"101" in response.content
    assert b"resident" in response.content
    assert b"202" not in response.content
    assert b"other" not in response.content
    assert b"outsider" not in response.content
    assert b"inactive_member" not in response.content


@pytest.mark.django_db
def test_unit_occupancy_create_creates_audit_log(client, core_context):
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_occupancy_create"),
        {
            "unit": str(unit.id),
            "user": str(core_context["resident"].id),
            "occupancy_type": OccupancyType.RESIDENT,
            "is_primary": "on",
            "starts_at": "2026-06-16",
            "ends_at": "",
        },
    )

    assert response.status_code == 302
    occupancy = UnitOccupancy.objects.get(
        condominium=core_context["condo_a"],
        unit=unit,
        user=core_context["resident"],
    )
    assert occupancy.is_primary is True
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.unit_occupancy.created",
        object_id=str(occupancy.id),
    ).exists()


@pytest.mark.django_db
def test_unit_occupancy_create_rejects_unit_from_other_condominium(client, core_context):
    other_unit = Unit.objects.create(condominium=core_context["condo_b"], number="202")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_occupancy_create"),
        {
            "unit": str(other_unit.id),
            "user": str(core_context["resident"].id),
            "occupancy_type": OccupancyType.RESIDENT,
        },
    )

    assert response.status_code == 200
    assert not UnitOccupancy.objects.filter(
        condominium=core_context["condo_a"],
        unit_id=other_unit.id,
    ).exists()


@pytest.mark.django_db
def test_unit_occupancy_create_rejects_user_without_active_membership(
    client,
    core_context,
    user_factory,
):
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    outsider = user_factory(username="outsider", email="outsider@example.com")
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(
        reverse("core:unit_occupancy_create"),
        {
            "unit": str(unit.id),
            "user": str(outsider.id),
            "occupancy_type": OccupancyType.RESIDENT,
        },
    )

    assert response.status_code == 200
    assert not UnitOccupancy.objects.filter(
        condominium=core_context["condo_a"],
        user=outsider,
    ).exists()


@pytest.mark.django_db
def test_syndic_deactivates_unit_occupancy_with_audit_log(client, core_context):
    unit = Unit.objects.create(condominium=core_context["condo_a"], number="101")
    occupancy = UnitOccupancy.objects.create(
        condominium=core_context["condo_a"],
        unit=unit,
        user=core_context["resident"],
        occupancy_type=OccupancyType.RESIDENT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:unit_occupancy_deactivate", args=[occupancy.id]))

    assert response.status_code == 302
    occupancy.refresh_from_db()
    assert occupancy.is_active is False
    assert AuditLog.objects.filter(
        condominium=core_context["condo_a"],
        actor=core_context["syndic"],
        action="core.unit_occupancy.deactivated",
        object_id=str(occupancy.id),
    ).exists()


@pytest.mark.django_db
def test_unit_occupancy_deactivate_blocks_cross_tenant_access(
    client,
    core_context,
    user_factory,
):
    other_user = user_factory(username="other", email="other@example.com")
    other_unit = Unit.objects.create(condominium=core_context["condo_b"], number="202")
    CondominiumMembership.objects.create(
        condominium=core_context["condo_b"],
        user=other_user,
        role=CondominiumRole.RESIDENT,
    )
    other_occupancy = UnitOccupancy.objects.create(
        condominium=core_context["condo_b"],
        unit=other_unit,
        user=other_user,
        occupancy_type=OccupancyType.RESIDENT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, core_context["condo_a"])

    response = client.post(reverse("core:unit_occupancy_deactivate", args=[other_occupancy.id]))

    assert response.status_code == 404
    other_occupancy.refresh_from_db()
    assert other_occupancy.is_active is True
