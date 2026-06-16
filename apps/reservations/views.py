from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from apps.core.permissions import require_active_membership, require_condominium_manager

from .forms import (
    AmenityForm,
    ReservationAdminFilterForm,
    ReservationDecisionForm,
    ReservationRequestForm,
)
from .selectors import (
    get_amenity_for_condominium,
    get_reservation_for_manager,
    get_reservation_for_user,
    list_amenities_for_condominium,
    list_reservations_for_manager,
    list_reservations_for_user,
)
from .services import (
    approve_reservation,
    cancel_reservation,
    create_amenity,
    deactivate_amenity,
    reject_reservation,
    request_reservation,
    update_amenity,
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
def reservation_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_active_membership(request.user, condominium)

    return render(
        request,
        "reservations/reservation_list.html",
        {
            "amenities": list_amenities_for_condominium(condominium=condominium),
            "reservations": list_reservations_for_user(
                condominium=condominium,
                user=request.user,
            ),
        },
    )


@login_required
def reservation_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_active_membership(request.user, condominium)

    form = ReservationRequestForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            reservation = request_reservation(
                condominium=condominium,
                actor=request.user,
                amenity=form.cleaned_data["amenity"],
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                notes=form.cleaned_data["notes"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Reserva solicitada.")
            return redirect("reservations:reservation_detail", reservation_id=reservation.id)

    return render(request, "reservations/reservation_form.html", {"form": form})


@login_required
def reservation_detail(request, reservation_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_active_membership(request.user, condominium)
    reservation = get_reservation_for_user(
        condominium=condominium,
        user=request.user,
        reservation_id=reservation_id,
    )

    return render(
        request,
        "reservations/reservation_detail.html",
        {"reservation": reservation},
    )


@login_required
def admin_reservation_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    filter_form = ReservationAdminFilterForm(request.GET or None, condominium=condominium)
    filters = filter_form.cleaned_data if filter_form.is_valid() else {}

    return render(
        request,
        "reservations/admin_reservation_list.html",
        {
            "filter_form": filter_form,
            "reservations": list_reservations_for_manager(
                condominium=condominium,
                filters=filters,
            ),
        },
    )


@login_required
def admin_reservation_detail(request, reservation_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    reservation = get_reservation_for_manager(
        condominium=condominium,
        reservation_id=reservation_id,
    )
    decision_form = ReservationDecisionForm()

    return render(
        request,
        "reservations/admin_reservation_detail.html",
        {"reservation": reservation, "decision_form": decision_form},
    )


@login_required
def reservation_approve(request, reservation_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    reservation = get_reservation_for_manager(
        condominium=condominium,
        reservation_id=reservation_id,
    )
    form = ReservationDecisionForm(request.POST)
    if form.is_valid():
        try:
            approve_reservation(
                condominium=condominium,
                actor=request.user,
                reservation=reservation,
                manager_notes=form.cleaned_data["manager_notes"],
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Reserva aprovada.")
    return redirect("reservations:admin_reservation_detail", reservation_id=reservation.id)


@login_required
def reservation_reject(request, reservation_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    reservation = get_reservation_for_manager(
        condominium=condominium,
        reservation_id=reservation_id,
    )
    form = ReservationDecisionForm(request.POST)
    if form.is_valid():
        try:
            reject_reservation(
                condominium=condominium,
                actor=request.user,
                reservation=reservation,
                manager_notes=form.cleaned_data["manager_notes"],
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Reserva rejeitada.")
    return redirect("reservations:admin_reservation_detail", reservation_id=reservation.id)


@login_required
def reservation_cancel(request, reservation_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    reservation = get_reservation_for_manager(
        condominium=condominium,
        reservation_id=reservation_id,
    )
    form = ReservationDecisionForm(request.POST)
    if form.is_valid():
        try:
            cancel_reservation(
                condominium=condominium,
                actor=request.user,
                reservation=reservation,
                manager_notes=form.cleaned_data["manager_notes"],
            )
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Reserva cancelada.")
    return redirect("reservations:admin_reservation_detail", reservation_id=reservation.id)


@login_required
def amenity_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "reservations/amenity_list.html",
        {"amenities": list_amenities_for_condominium(condominium=condominium)},
    )


@login_required
def amenity_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = AmenityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_amenity(
                condominium=condominium,
                actor=request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                rules=form.cleaned_data["rules"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Area comum cadastrada.")
            return redirect("reservations:amenity_list")

    return render(request, "reservations/amenity_form.html", {"form": form})


@login_required
def amenity_update(request, amenity_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    amenity = get_amenity_for_condominium(condominium=condominium, amenity_id=amenity_id)

    form = AmenityForm(
        request.POST or None,
        initial={
            "name": amenity.name,
            "description": amenity.description,
            "rules": amenity.rules,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_amenity(
                condominium=condominium,
                actor=request.user,
                amenity=amenity,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                rules=form.cleaned_data["rules"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Area comum atualizada.")
            return redirect("reservations:amenity_list")

    return render(
        request,
        "reservations/amenity_form.html",
        {"form": form, "is_update": True},
    )


@login_required
def amenity_deactivate(request, amenity_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    amenity = get_amenity_for_condominium(condominium=condominium, amenity_id=amenity_id)

    if request.method == "POST":
        try:
            deactivate_amenity(condominium=condominium, actor=request.user, amenity=amenity)
        except ValidationError as error:
            _message_validation_error(request, error)
        else:
            messages.success(request, "Area comum desativada.")
            return redirect("reservations:amenity_list")

    return render(
        request,
        "core/deactivate_confirm.html",
        {
            "title": "Desativar area comum",
            "object_label": amenity.name,
            "cancel_url_name": "reservations:amenity_list",
        },
    )
