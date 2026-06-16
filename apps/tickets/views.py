from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from apps.core.permissions import require_condominium_manager

from .forms import TicketAdminUpdateForm, TicketCategoryForm, TicketCommentForm, TicketCreateForm
from .selectors import (
    get_ticket_category_for_condominium,
    get_ticket_for_manager,
    get_ticket_for_user,
    list_ticket_categories_for_condominium,
    list_ticket_comments_for_manager,
    list_ticket_comments_for_user,
    list_tickets_for_manager,
    list_tickets_for_user,
)
from .services import (
    add_ticket_comment,
    create_ticket,
    create_ticket_category,
    deactivate_ticket_category,
    update_ticket_admin,
    update_ticket_category,
)


def _active_condominium_or_redirect(request):
    if request.condominium is None:
        return None, redirect("core:condominium_select")
    return request.condominium, None


def _add_validation_error(form, error):
    if hasattr(error, "error_dict"):
        for field, messages_list in error.message_dict.items():
            target_field = field if field in form.fields else None
            for message in messages_list:
                form.add_error(target_field, message)
        return
    if hasattr(error, "messages"):
        for message in error.messages:
            form.add_error(None, message)
        return
    form.add_error(None, str(error))


def _message_validation_error(request, error):
    messages.error(request, "; ".join(error.messages))


@login_required
def ticket_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response

    return render(
        request,
        "tickets/ticket_list.html",
        {"tickets": list_tickets_for_user(condominium=condominium, user=request.user)},
    )


@login_required
def ticket_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response

    form = TicketCreateForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            ticket = create_ticket(
                condominium=condominium,
                actor=request.user,
                category=form.cleaned_data["category"],
                unit=form.cleaned_data["unit"],
                priority=form.cleaned_data["priority"],
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
            )
        except (PermissionDenied, ValidationError) as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Chamado aberto.")
            return redirect("tickets:ticket_detail", ticket_id=ticket.id)

    return render(request, "tickets/ticket_form.html", {"form": form})


@login_required
def ticket_detail(request, ticket_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    ticket = get_ticket_for_user(
        condominium=condominium,
        user=request.user,
        ticket_id=ticket_id,
    )
    comment_form = TicketCommentForm(request.POST or None, allow_internal=False)
    if request.method == "POST" and comment_form.is_valid():
        try:
            add_ticket_comment(
                condominium=condominium,
                actor=request.user,
                ticket=ticket,
                message=comment_form.cleaned_data["message"],
                is_internal=False,
            )
        except (PermissionDenied, ValidationError) as error:
            _add_validation_error(comment_form, error)
        else:
            messages.success(request, "Comentario adicionado.")
            return redirect("tickets:ticket_detail", ticket_id=ticket.id)

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "comments": list_ticket_comments_for_user(
                condominium=condominium,
                ticket=ticket,
                user=request.user,
            ),
            "comment_form": comment_form,
        },
    )


@login_required
def admin_ticket_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "tickets/admin_ticket_list.html",
        {"tickets": list_tickets_for_manager(condominium=condominium)},
    )


@login_required
def admin_ticket_detail(request, ticket_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    ticket = get_ticket_for_manager(condominium=condominium, ticket_id=ticket_id)

    update_form = TicketAdminUpdateForm(
        request.POST if request.POST.get("action") == "update_ticket" else None,
        condominium=condominium,
        initial={
            "status": ticket.status,
            "priority": ticket.priority,
            "assigned_to": ticket.assigned_to_id,
        },
    )
    comment_form = TicketCommentForm(
        request.POST if request.POST.get("action") == "add_comment" else None,
        allow_internal=True,
    )

    if request.method == "POST" and request.POST.get("action") == "update_ticket":
        if update_form.is_valid():
            try:
                update_ticket_admin(
                    condominium=condominium,
                    actor=request.user,
                    ticket=ticket,
                    status=update_form.cleaned_data["status"],
                    priority=update_form.cleaned_data["priority"],
                    assigned_to=update_form.cleaned_data["assigned_to"],
                )
            except ValidationError as error:
                _add_validation_error(update_form, error)
            else:
                messages.success(request, "Chamado atualizado.")
                return redirect("tickets:admin_ticket_detail", ticket_id=ticket.id)

    if request.method == "POST" and request.POST.get("action") == "add_comment":
        if comment_form.is_valid():
            try:
                add_ticket_comment(
                    condominium=condominium,
                    actor=request.user,
                    ticket=ticket,
                    message=comment_form.cleaned_data["message"],
                    is_internal=comment_form.cleaned_data["is_internal"],
                )
            except (PermissionDenied, ValidationError) as error:
                _add_validation_error(comment_form, error)
            else:
                messages.success(request, "Comentario adicionado.")
                return redirect("tickets:admin_ticket_detail", ticket_id=ticket.id)

    return render(
        request,
        "tickets/admin_ticket_detail.html",
        {
            "ticket": ticket,
            "comments": list_ticket_comments_for_manager(
                condominium=condominium,
                ticket=ticket,
            ),
            "update_form": update_form,
            "comment_form": comment_form,
        },
    )


@login_required
def category_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "tickets/category_list.html",
        {"categories": list_ticket_categories_for_condominium(condominium=condominium)},
    )


@login_required
def category_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = TicketCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_ticket_category(
                condominium=condominium,
                actor=request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Categoria cadastrada.")
            return redirect("tickets:category_list")

    return render(request, "tickets/category_form.html", {"form": form})


@login_required
def category_update(request, category_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    category = get_ticket_category_for_condominium(
        condominium=condominium,
        category_id=category_id,
    )

    form = TicketCategoryForm(
        request.POST or None,
        initial={"name": category.name, "description": category.description},
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_ticket_category(
                condominium=condominium,
                actor=request.user,
                category=category,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Categoria atualizada.")
            return redirect("tickets:category_list")

    return render(
        request,
        "tickets/category_form.html",
        {"form": form, "is_update": True},
    )


@login_required
def category_deactivate(request, category_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    category = get_ticket_category_for_condominium(
        condominium=condominium,
        category_id=category_id,
    )

    if request.method == "POST":
        try:
            deactivate_ticket_category(
                condominium=condominium,
                actor=request.user,
                category=category,
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Categoria desativada.")
            return redirect("tickets:category_list")

    return render(
        request,
        "core/deactivate_confirm.html",
        {
            "title": "Desativar categoria de chamado",
            "object_label": category.name,
            "cancel_url_name": "tickets:category_list",
        },
    )
