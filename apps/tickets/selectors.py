from django.http import Http404

from .models import Ticket, TicketCategory, TicketComment


def list_ticket_categories_for_condominium(*, condominium):
    return TicketCategory.active_objects.filter(condominium=condominium).order_by("name")


def get_ticket_category_for_condominium(*, condominium, category_id):
    category = TicketCategory.active_objects.filter(
        id=category_id,
        condominium=condominium,
    ).first()
    if category is None:
        raise Http404("Categoria de chamado nao encontrada.")
    return category


def list_tickets_for_user(*, condominium, user):
    return (
        Ticket.active_objects.filter(condominium=condominium, created_by=user)
        .select_related("category", "unit", "created_by", "assigned_to")
        .order_by("-created_at")
    )


def list_tickets_for_manager(*, condominium, filters=None):
    filters = filters or {}
    tickets = Ticket.active_objects.filter(condominium=condominium)
    if filters.get("status"):
        tickets = tickets.filter(status=filters["status"])
    if filters.get("priority"):
        tickets = tickets.filter(priority=filters["priority"])
    if filters.get("category"):
        tickets = tickets.filter(category=filters["category"])
    return (
        tickets.select_related("category", "unit", "created_by", "assigned_to")
        .order_by("-created_at")
    )


def get_ticket_for_user(*, condominium, user, ticket_id):
    ticket = (
        Ticket.active_objects.select_related("category", "unit", "created_by", "assigned_to")
        .filter(id=ticket_id, condominium=condominium, created_by=user)
        .first()
    )
    if ticket is None:
        raise Http404("Chamado nao encontrado.")
    return ticket


def get_ticket_for_manager(*, condominium, ticket_id):
    ticket = (
        Ticket.active_objects.select_related("category", "unit", "created_by", "assigned_to")
        .filter(id=ticket_id, condominium=condominium)
        .first()
    )
    if ticket is None:
        raise Http404("Chamado nao encontrado.")
    return ticket


def list_ticket_comments_for_user(*, condominium, ticket, user):
    return (
        TicketComment.objects.filter(
            condominium=condominium,
            ticket=ticket,
            ticket__created_by=user,
            is_internal=False,
        )
        .select_related("author")
        .order_by("created_at")
    )


def list_ticket_comments_for_manager(*, condominium, ticket):
    return (
        TicketComment.objects.filter(condominium=condominium, ticket=ticket)
        .select_related("author")
        .order_by("created_at")
    )
