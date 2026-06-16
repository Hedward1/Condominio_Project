from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import create_audit_log
from apps.core.models import CondominiumMembership, Unit
from apps.core.permissions import (
    require_active_membership,
    require_condominium_manager,
    user_can_manage_condominium,
)

from .models import Ticket, TicketCategory, TicketComment, TicketPriority, TicketStatus


def _validate_ticket_condominium(*, condominium, ticket: Ticket):
    if ticket.condominium_id != condominium.id:
        raise ValidationError({"ticket": "O chamado pertence a outro condominio."})


def _validate_category_condominium(*, condominium, category: TicketCategory | None):
    if category is not None and category.condominium_id != condominium.id:
        raise ValidationError({"category": "A categoria pertence a outro condominio."})


def _validate_unit_condominium(*, condominium, unit: Unit | None):
    if unit is not None and unit.condominium_id != condominium.id:
        raise ValidationError({"unit": "A unidade pertence a outro condominio."})


def _validate_assignee_membership(*, condominium, assigned_to):
    if assigned_to is None:
        return
    if not CondominiumMembership.active_objects.filter(
        condominium=condominium,
        user=assigned_to,
    ).exists():
        raise ValidationError({"assigned_to": "O responsavel deve ser membro ativo do condominio."})


def _validate_unique_active_category_name(
    *,
    condominium,
    name: str,
    category: TicketCategory | None = None,
):
    duplicate_query = TicketCategory.active_objects.filter(
        condominium=condominium,
        name__iexact=name.strip(),
    )
    if category is not None:
        duplicate_query = duplicate_query.exclude(id=category.id)
    if duplicate_query.exists():
        raise ValidationError({"name": "Ja existe uma categoria ativa com este nome."})


def _require_ticket_comment_access(*, condominium, actor, ticket: Ticket) -> bool:
    is_manager = user_can_manage_condominium(actor, condominium)
    if is_manager:
        return True

    require_active_membership(actor, condominium)
    if ticket.created_by_id != actor.id:
        raise PermissionDenied("Voce nao tem acesso a este chamado.")
    return False


def _require_ticket_create_access(*, condominium, actor):
    if user_can_manage_condominium(actor, condominium):
        return
    require_active_membership(actor, condominium)


@transaction.atomic
def create_ticket_category(
    *,
    condominium,
    actor,
    name: str,
    description: str = "",
) -> TicketCategory:
    require_condominium_manager(actor, condominium)
    _validate_unique_active_category_name(condominium=condominium, name=name)

    category = TicketCategory(
        condominium=condominium,
        name=name.strip(),
        description=description,
        created_by=actor,
        updated_by=actor,
    )
    category.full_clean()
    category.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="tickets.ticket_category.created",
        target=category,
    )
    return category


@transaction.atomic
def update_ticket_category(
    *,
    condominium,
    actor,
    category: TicketCategory,
    name: str,
    description: str = "",
) -> TicketCategory:
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)
    _validate_unique_active_category_name(
        condominium=condominium,
        name=name,
        category=category,
    )

    changes = {
        "name": {"from": category.name, "to": name.strip()},
        "description": {"from": category.description, "to": description},
    }
    category.name = name.strip()
    category.description = description
    category.updated_by = actor
    category.full_clean()
    category.save(update_fields=["name", "description", "updated_by", "updated_at"])
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="tickets.ticket_category.updated",
        target=category,
        changes=changes,
    )
    return category


@transaction.atomic
def deactivate_ticket_category(*, condominium, actor, category: TicketCategory) -> TicketCategory:
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)
    if Ticket.active_objects.filter(condominium=condominium, category=category).exists():
        raise ValidationError(
            {"category": "Esta categoria possui chamados ativos. Reclassifique os chamados primeiro."},
        )

    category.soft_delete(user=actor)
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="tickets.ticket_category.deactivated",
        target=category,
    )
    return category


@transaction.atomic
def create_ticket(
    *,
    condominium,
    actor,
    title: str,
    description: str,
    category: TicketCategory | None = None,
    unit: Unit | None = None,
    priority: TicketPriority | str = TicketPriority.NORMAL,
) -> Ticket:
    _require_ticket_create_access(condominium=condominium, actor=actor)
    _validate_category_condominium(condominium=condominium, category=category)
    _validate_unit_condominium(condominium=condominium, unit=unit)

    ticket = Ticket(
        condominium=condominium,
        category=category,
        unit=unit,
        title=title,
        description=description,
        priority=priority,
        status=TicketStatus.OPEN,
        created_by=actor,
        updated_by=actor,
    )
    ticket.full_clean()
    ticket.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="tickets.ticket.created",
        target=ticket,
    )
    return ticket


@transaction.atomic
def update_ticket_admin(
    *,
    condominium,
    actor,
    ticket: Ticket,
    status: TicketStatus | str,
    priority: TicketPriority | str,
    assigned_to=None,
) -> Ticket:
    require_condominium_manager(actor, condominium)
    _validate_ticket_condominium(condominium=condominium, ticket=ticket)
    _validate_assignee_membership(condominium=condominium, assigned_to=assigned_to)

    old_status = ticket.status
    old_priority = ticket.priority
    old_assigned_to_id = ticket.assigned_to_id

    ticket.status = status
    ticket.priority = priority
    ticket.assigned_to = assigned_to
    if old_status != status and status == TicketStatus.RESOLVED and ticket.resolved_at is None:
        ticket.resolved_at = timezone.now()
    if old_status != status and status == TicketStatus.CLOSED and ticket.closed_at is None:
        ticket.closed_at = timezone.now()
    ticket.updated_by = actor
    ticket.full_clean()
    ticket.save(
        update_fields=[
            "status",
            "priority",
            "assigned_to",
            "resolved_at",
            "closed_at",
            "updated_by",
            "updated_at",
        ],
    )

    if old_status != ticket.status:
        create_audit_log(
            condominium=condominium,
            actor=actor,
            action="tickets.ticket.status_changed",
            target=ticket,
            changes={"status": {"from": old_status, "to": ticket.status}},
        )
    if old_priority != ticket.priority:
        create_audit_log(
            condominium=condominium,
            actor=actor,
            action="tickets.ticket.priority_changed",
            target=ticket,
            changes={"priority": {"from": old_priority, "to": ticket.priority}},
        )
    if old_assigned_to_id != ticket.assigned_to_id:
        create_audit_log(
            condominium=condominium,
            actor=actor,
            action="tickets.ticket.assigned_changed",
            target=ticket,
            changes={
                "assigned_to_id": {
                    "from": str(old_assigned_to_id or ""),
                    "to": str(ticket.assigned_to_id or ""),
                },
            },
        )
    return ticket


@transaction.atomic
def add_ticket_comment(
    *,
    condominium,
    actor,
    ticket: Ticket,
    message: str,
    is_internal: bool = False,
) -> TicketComment:
    _validate_ticket_condominium(condominium=condominium, ticket=ticket)
    is_manager = _require_ticket_comment_access(
        condominium=condominium,
        actor=actor,
        ticket=ticket,
    )
    if is_internal and not is_manager:
        raise PermissionDenied("Voce nao pode criar comentario interno.")

    comment = TicketComment(
        condominium=condominium,
        ticket=ticket,
        author=actor,
        message=message,
        is_internal=is_internal,
    )
    comment.full_clean()
    comment.save()
    if is_manager or is_internal:
        create_audit_log(
            condominium=condominium,
            actor=actor,
            action="tickets.ticket_comment.created",
            target=comment,
            metadata={"ticket_id": str(ticket.id), "is_internal": is_internal},
        )
    return comment
