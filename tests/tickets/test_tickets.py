from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Condominium, CondominiumMembership, CondominiumRole, Unit
from apps.dashboard.selectors import get_syndic_dashboard_summary
from apps.tickets.models import (
    Ticket,
    TicketCategory,
    TicketComment,
    TicketPriority,
    TicketStatus,
)
from apps.tickets.selectors import list_tickets_for_manager, list_tickets_for_user
from apps.tickets.services import add_ticket_comment, create_ticket, update_ticket_admin


def activate_condominium(client, condominium):
    session = client.session
    session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    session.save()


@pytest.fixture
def tickets_context(db, user_factory):
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    syndic = user_factory(username="syndic", email="syndic@example.com")
    resident = user_factory(username="resident", email="resident@example.com")
    second_resident = user_factory(username="resident2", email="resident2@example.com")
    other_resident = user_factory(username="other", email="other@example.com")
    for user, condo, role in (
        (syndic, condo_a, CondominiumRole.SYNDIC),
        (resident, condo_a, CondominiumRole.RESIDENT),
        (second_resident, condo_a, CondominiumRole.RESIDENT),
        (other_resident, condo_b, CondominiumRole.RESIDENT),
    ):
        CondominiumMembership.objects.create(condominium=condo, user=user, role=role)
    unit_a = Unit.objects.create(condominium=condo_a, number="101")
    unit_b = Unit.objects.create(condominium=condo_b, number="202")
    category_a = TicketCategory.objects.create(condominium=condo_a, name="Manutencao")
    category_b = TicketCategory.objects.create(condominium=condo_b, name="Outro condominio")
    return {
        "condo_a": condo_a,
        "condo_b": condo_b,
        "syndic": syndic,
        "resident": resident,
        "second_resident": second_resident,
        "other_resident": other_resident,
        "unit_a": unit_a,
        "unit_b": unit_b,
        "category_a": category_a,
        "category_b": category_b,
    }


def make_ticket(*, condominium, created_by, title="Ticket", **kwargs):
    defaults = {
        "description": "Descricao do chamado",
        "status": TicketStatus.OPEN,
        "priority": TicketPriority.NORMAL,
    }
    defaults.update(kwargs)
    return Ticket.objects.create(
        condominium=condominium,
        created_by=created_by,
        updated_by=created_by,
        title=title,
        **defaults,
    )


@pytest.mark.django_db
def test_resident_opens_ticket_with_audit_log(client, tickets_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_create"),
        {
            "category": str(tickets_context["category_a"].id),
            "unit": str(tickets_context["unit_a"].id),
            "priority": TicketPriority.HIGH,
            "title": "Vazamento",
            "description": "Ha vazamento na garagem.",
        },
    )

    assert response.status_code == 302
    ticket = Ticket.objects.get(condominium=tickets_context["condo_a"], title="Vazamento")
    assert ticket.created_by == tickets_context["resident"]
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.HIGH
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        actor=tickets_context["resident"],
        action="tickets.ticket.created",
        object_id=str(ticket.id),
    ).exists()


@pytest.mark.django_db
def test_resident_sees_only_own_tickets(client, tickets_context):
    own_ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        title="Meu chamado",
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["second_resident"],
        title="Chamado de outro morador",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.get(reverse("tickets:ticket_list"))

    assert response.status_code == 200
    assert own_ticket.title.encode() in response.content
    assert b"Chamado de outro morador" not in response.content


@pytest.mark.django_db
def test_resident_cannot_view_other_residents_ticket(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["second_resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.get(reverse("tickets:ticket_detail", args=[ticket.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_resident_does_not_see_ticket_from_other_condominium(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
        title="Ticket condo B",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    list_response = client.get(reverse("tickets:ticket_list"))
    detail_response = client.get(reverse("tickets:ticket_detail", args=[ticket.id]))

    assert list_response.status_code == 200
    assert b"Ticket condo B" not in list_response.content
    assert detail_response.status_code == 404


@pytest.mark.django_db
def test_manager_sees_all_tickets_from_active_condominium(client, tickets_context):
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        title="Chamado A1",
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["second_resident"],
        title="Chamado A2",
    )
    make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
        title="Chamado B",
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.get(reverse("tickets:admin_ticket_list"))

    assert response.status_code == 200
    assert b"Chamado A1" in response.content
    assert b"Chamado A2" in response.content
    assert b"Chamado B" not in response.content


@pytest.mark.django_db
def test_manager_does_not_see_ticket_from_other_condominium(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.get(reverse("tickets:admin_ticket_detail", args=[ticket.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_open_ticket_rejects_unit_from_other_condominium(client, tickets_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_create"),
        {
            "category": str(tickets_context["category_a"].id),
            "unit": str(tickets_context["unit_b"].id),
            "priority": TicketPriority.NORMAL,
            "title": "Unidade invalida",
            "description": "Nao deve salvar.",
        },
    )

    assert response.status_code == 200
    assert not Ticket.objects.filter(
        condominium=tickets_context["condo_a"],
        title="Unidade invalida",
    ).exists()


@pytest.mark.django_db
def test_open_ticket_rejects_category_from_other_condominium(client, tickets_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_create"),
        {
            "category": str(tickets_context["category_b"].id),
            "unit": str(tickets_context["unit_a"].id),
            "priority": TicketPriority.NORMAL,
            "title": "Categoria invalida",
            "description": "Nao deve salvar.",
        },
    )

    assert response.status_code == 200
    assert not Ticket.objects.filter(
        condominium=tickets_context["condo_a"],
        title="Categoria invalida",
    ).exists()


@pytest.mark.django_db
def test_manager_changes_status_with_audit_log(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {
            "action": "update_ticket",
            "status": TicketStatus.IN_PROGRESS,
            "priority": TicketPriority.NORMAL,
            "assigned_to": "",
        },
    )

    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        actor=tickets_context["syndic"],
        action="tickets.ticket.status_changed",
        object_id=str(ticket.id),
    ).exists()


@pytest.mark.django_db
def test_manager_changes_priority_with_audit_log(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {
            "action": "update_ticket",
            "status": TicketStatus.OPEN,
            "priority": TicketPriority.URGENT,
            "assigned_to": "",
        },
    )

    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.priority == TicketPriority.URGENT
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        actor=tickets_context["syndic"],
        action="tickets.ticket.priority_changed",
        object_id=str(ticket.id),
    ).exists()


@pytest.mark.django_db
def test_manager_changes_assignee_with_audit_log(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {
            "action": "update_ticket",
            "status": TicketStatus.OPEN,
            "priority": TicketPriority.NORMAL,
            "assigned_to": str(tickets_context["syndic"].id),
        },
    )

    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.assigned_to == tickets_context["syndic"]
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        actor=tickets_context["syndic"],
        action="tickets.ticket.assigned_changed",
        object_id=str(ticket.id),
    ).exists()


@pytest.mark.django_db
def test_manager_cannot_assign_ticket_to_user_from_other_condominium(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {
            "action": "update_ticket",
            "status": TicketStatus.OPEN,
            "priority": TicketPriority.NORMAL,
            "assigned_to": str(tickets_context["other_resident"].id),
        },
    )

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.assigned_to is None
    assert not AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        action="tickets.ticket.assigned_changed",
        object_id=str(ticket.id),
    ).exists()


@pytest.mark.django_db
def test_resident_cannot_change_admin_fields(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {
            "action": "update_ticket",
            "status": TicketStatus.RESOLVED,
            "priority": TicketPriority.URGENT,
            "assigned_to": str(tickets_context["resident"].id),
        },
    )

    assert response.status_code == 403
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.NORMAL
    assert ticket.assigned_to is None


@pytest.mark.django_db
def test_resident_comments_on_own_ticket(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_detail", args=[ticket.id]),
        {"message": "Comentario do morador"},
    )

    assert response.status_code == 302
    assert TicketComment.objects.filter(
        condominium=tickets_context["condo_a"],
        ticket=ticket,
        author=tickets_context["resident"],
        message="Comentario do morador",
        is_internal=False,
    ).exists()


@pytest.mark.django_db
def test_resident_cannot_comment_on_other_residents_ticket(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["second_resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_detail", args=[ticket.id]),
        {"message": "Tentativa indevida"},
    )

    assert response.status_code == 404
    assert not TicketComment.objects.filter(ticket=ticket, message="Tentativa indevida").exists()


@pytest.mark.django_db
def test_manager_comments_on_any_ticket_with_audit_log(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:admin_ticket_detail", args=[ticket.id]),
        {"action": "add_comment", "message": "Comentario administrativo"},
    )

    assert response.status_code == 302
    comment = TicketComment.objects.get(ticket=ticket, message="Comentario administrativo")
    assert comment.author == tickets_context["syndic"]
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        actor=tickets_context["syndic"],
        action="tickets.ticket_comment.created",
        object_id=str(comment.id),
    ).exists()


@pytest.mark.django_db
def test_internal_comment_visible_only_to_manager(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    TicketComment.objects.create(
        condominium=tickets_context["condo_a"],
        ticket=ticket,
        author=tickets_context["syndic"],
        message="Nota interna",
        is_internal=True,
    )
    TicketComment.objects.create(
        condominium=tickets_context["condo_a"],
        ticket=ticket,
        author=tickets_context["syndic"],
        message="Comentario publico",
    )

    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])
    resident_response = client.get(reverse("tickets:ticket_detail", args=[ticket.id]))
    client.logout()
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])
    manager_response = client.get(reverse("tickets:admin_ticket_detail", args=[ticket.id]))

    assert b"Comentario publico" in resident_response.content
    assert b"Nota interna" not in resident_response.content
    assert b"Nota interna" in manager_response.content


@pytest.mark.django_db
def test_resident_posted_internal_flag_does_not_create_internal_comment(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:ticket_detail", args=[ticket.id]),
        {"message": "Nao deve ser interno", "is_internal": "on"},
    )

    assert response.status_code == 302
    comment = TicketComment.objects.get(ticket=ticket, message="Nao deve ser interno")
    assert comment.is_internal is False


@pytest.mark.django_db
def test_resident_cannot_access_ticket_category_management(client, tickets_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.get(reverse("tickets:category_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_creates_updates_and_deactivates_ticket_category_with_audit_log(
    client,
    tickets_context,
):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    create_response = client.post(
        reverse("tickets:category_create"),
        {"name": "Seguranca", "description": "Portoes e acesso"},
    )
    category = TicketCategory.objects.get(condominium=tickets_context["condo_a"], name="Seguranca")
    update_response = client.post(
        reverse("tickets:category_update", args=[category.id]),
        {"name": "Seguranca predial", "description": "Controle de acesso"},
    )
    deactivate_response = client.post(reverse("tickets:category_deactivate", args=[category.id]))

    assert create_response.status_code == 302
    assert update_response.status_code == 302
    assert deactivate_response.status_code == 302
    category.refresh_from_db()
    assert category.is_active is False
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        action="tickets.ticket_category.created",
        object_id=str(category.id),
    ).exists()
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        action="tickets.ticket_category.updated",
        object_id=str(category.id),
    ).exists()
    assert AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        action="tickets.ticket_category.deactivated",
        object_id=str(category.id),
    ).exists()


@pytest.mark.django_db
def test_duplicate_active_ticket_category_is_rejected(client, tickets_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:category_create"),
        {"name": "manutencao", "description": "Duplicada"},
    )

    assert response.status_code == 200
    assert TicketCategory.active_objects.filter(
        condominium=tickets_context["condo_a"],
        name__iexact="Manutencao",
    ).count() == 1


@pytest.mark.django_db
def test_ticket_category_with_active_ticket_cannot_be_deactivated(client, tickets_context):
    ticket = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        category=tickets_context["category_a"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, tickets_context["condo_a"])

    response = client.post(
        reverse("tickets:category_deactivate", args=[tickets_context["category_a"].id]),
    )

    tickets_context["category_a"].refresh_from_db()
    assert response.status_code == 200
    assert ticket.is_active is True
    assert tickets_context["category_a"].is_active is True
    assert not AuditLog.objects.filter(
        condominium=tickets_context["condo_a"],
        action="tickets.ticket_category.deactivated",
        object_id=str(tickets_context["category_a"].id),
    ).exists()


@pytest.mark.django_db
def test_dashboard_ticket_indicators_do_not_break_without_tickets(tickets_context):
    summary = get_syndic_dashboard_summary(condominium=tickets_context["condo_a"])

    assert summary["open_tickets"] == 0
    assert summary["tickets_in_progress"] == 0
    assert summary["tickets_resolved_this_month"] == 0


@pytest.mark.django_db
def test_dashboard_counts_open_in_progress_and_resolved_this_month(tickets_context):
    now = timezone.now()
    old_date = now - timedelta(days=40)
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        status=TicketStatus.OPEN,
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        status=TicketStatus.IN_PROGRESS,
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        status=TicketStatus.RESOLVED,
        resolved_at=now,
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        status=TicketStatus.RESOLVED,
        resolved_at=old_date,
    )
    make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
        status=TicketStatus.OPEN,
    )

    summary = get_syndic_dashboard_summary(condominium=tickets_context["condo_a"])

    assert summary["open_tickets"] == 1
    assert summary["tickets_in_progress"] == 1
    assert summary["tickets_resolved_this_month"] == 1


@pytest.mark.django_db
def test_ticket_services_block_cross_tenant_actions(tickets_context):
    ticket_b = make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
    )

    with pytest.raises(ValidationError):
        create_ticket(
            condominium=tickets_context["condo_a"],
            actor=tickets_context["resident"],
            title="Categoria cruzada",
            description="Nao deve salvar",
            category=tickets_context["category_b"],
        )

    with pytest.raises(ValidationError):
        create_ticket(
            condominium=tickets_context["condo_a"],
            actor=tickets_context["resident"],
            title="Unidade cruzada",
            description="Nao deve salvar",
            unit=tickets_context["unit_b"],
        )

    with pytest.raises(ValidationError):
        update_ticket_admin(
            condominium=tickets_context["condo_a"],
            actor=tickets_context["syndic"],
            ticket=ticket_b,
            status=TicketStatus.IN_PROGRESS,
            priority=TicketPriority.HIGH,
        )

    ticket_a = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
    )
    with pytest.raises(ValidationError):
        update_ticket_admin(
            condominium=tickets_context["condo_a"],
            actor=tickets_context["syndic"],
            ticket=ticket_a,
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            assigned_to=tickets_context["other_resident"],
        )

    with pytest.raises(ValidationError):
        add_ticket_comment(
            condominium=tickets_context["condo_a"],
            actor=tickets_context["syndic"],
            ticket=ticket_b,
            message="Comentario cruzado",
        )


@pytest.mark.django_db
def test_ticket_selectors_filter_by_condominium_and_user(tickets_context):
    ticket_a = make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["resident"],
        title="Ticket A",
    )
    make_ticket(
        condominium=tickets_context["condo_a"],
        created_by=tickets_context["second_resident"],
        title="Ticket outro morador",
    )
    make_ticket(
        condominium=tickets_context["condo_b"],
        created_by=tickets_context["other_resident"],
        title="Ticket B",
    )

    manager_tickets = list(list_tickets_for_manager(condominium=tickets_context["condo_a"]))
    resident_tickets = list(
        list_tickets_for_user(
            condominium=tickets_context["condo_a"],
            user=tickets_context["resident"],
        ),
    )

    assert {ticket.title for ticket in manager_tickets} == {"Ticket A", "Ticket outro morador"}
    assert resident_tickets == [ticket_a]
