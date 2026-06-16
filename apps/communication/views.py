from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from apps.core.permissions import require_condominium_manager

from .forms import AnnouncementForm
from .selectors import (
    get_announcement_for_condominium,
    get_draft_announcement_for_condominium,
    get_published_announcement_for_condominium,
    has_user_read_announcement,
    list_admin_announcements_for_condominium,
    list_published_announcements_for_condominium,
)
from .services import (
    archive_announcement,
    create_announcement,
    mark_announcement_as_read,
    publish_announcement,
    update_draft_announcement,
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
    form.add_error(None, error)


def _message_validation_error(request, error):
    messages.error(request, "; ".join(error.messages))


@login_required
def admin_announcement_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "communication/admin_announcement_list.html",
        {
            "announcements": list_admin_announcements_for_condominium(
                condominium=condominium,
            ),
        },
    )


@login_required
def announcement_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = AnnouncementForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            create_announcement(
                condominium=condominium,
                actor=request.user,
                category=form.cleaned_data["category"],
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
                is_pinned=form.cleaned_data["is_pinned"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Comunicado salvo como rascunho.")
            return redirect("communication:admin_announcement_list")

    return render(request, "communication/announcement_form.html", {"form": form})


@login_required
def announcement_update(request, announcement_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    announcement = get_draft_announcement_for_condominium(
        condominium=condominium,
        announcement_id=announcement_id,
    )

    form = AnnouncementForm(
        request.POST or None,
        condominium=condominium,
        initial={
            "category": announcement.category_id,
            "title": announcement.title,
            "content": announcement.content,
            "is_pinned": announcement.is_pinned,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_draft_announcement(
                condominium=condominium,
                actor=request.user,
                announcement=announcement,
                category=form.cleaned_data["category"],
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
                is_pinned=form.cleaned_data["is_pinned"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Comunicado atualizado.")
            return redirect("communication:admin_announcement_list")

    return render(
        request,
        "communication/announcement_form.html",
        {"form": form, "is_update": True},
    )


@login_required
def announcement_publish(request, announcement_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    announcement = get_announcement_for_condominium(
        condominium=condominium,
        announcement_id=announcement_id,
    )

    if request.method == "POST":
        try:
            publish_announcement(
                condominium=condominium,
                actor=request.user,
                announcement=announcement,
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Comunicado publicado.")
    return redirect("communication:admin_announcement_list")


@login_required
def announcement_archive(request, announcement_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    announcement = get_announcement_for_condominium(
        condominium=condominium,
        announcement_id=announcement_id,
    )

    if request.method == "POST":
        try:
            archive_announcement(
                condominium=condominium,
                actor=request.user,
                announcement=announcement,
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Comunicado arquivado.")
    return redirect("communication:admin_announcement_list")


@login_required
def mural(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response

    return render(
        request,
        "communication/mural.html",
        {
            "announcements": list_published_announcements_for_condominium(
                condominium=condominium,
            ),
        },
    )


@login_required
def announcement_detail(request, announcement_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    announcement = get_published_announcement_for_condominium(
        condominium=condominium,
        announcement_id=announcement_id,
    )

    return render(
        request,
        "communication/announcement_detail.html",
        {
            "announcement": announcement,
            "has_read": has_user_read_announcement(
                condominium=condominium,
                announcement=announcement,
                user=request.user,
            ),
        },
    )


@login_required
def announcement_mark_read(request, announcement_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    announcement = get_published_announcement_for_condominium(
        condominium=condominium,
        announcement_id=announcement_id,
    )

    if request.method == "POST":
        try:
            mark_announcement_as_read(
                condominium=condominium,
                user=request.user,
                announcement=announcement,
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Leitura confirmada.")
    return redirect("communication:announcement_detail", announcement_id=announcement.id)
