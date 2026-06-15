from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from .forms import BlockForm, MembershipCreateForm, UnitForm
from .permissions import require_condominium_manager
from .selectors import (
    list_blocks_for_condominium,
    list_condominiums_for_user,
    list_memberships_for_condominium,
    list_units_for_condominium,
)
from .services import (
    create_block,
    create_unit,
    create_user_membership,
    set_active_condominium_for_request,
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


@login_required
def condominium_select(request):
    condominiums = list_condominiums_for_user(request.user)

    if request.method == "POST":
        condominium_id = request.POST.get("condominium_id")
        try:
            set_active_condominium_for_request(
                request=request,
                condominium_id=condominium_id,
            )
        except (PermissionDenied, ValidationError):
            messages.error(request, "Voce nao tem acesso a este condominio.")
        else:
            return redirect("dashboard:home")

    return render(
        request,
        "core/condominium_select.html",
        {"condominiums": condominiums},
    )


@login_required
def block_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "core/block_list.html",
        {"blocks": list_blocks_for_condominium(condominium=condominium)},
    )


@login_required
def block_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = BlockForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_block(
                condominium=condominium,
                actor=request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Bloco cadastrado.")
            return redirect("core:block_list")

    return render(request, "core/block_form.html", {"form": form})


@login_required
def unit_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "core/unit_list.html",
        {"units": list_units_for_condominium(condominium=condominium)},
    )


@login_required
def unit_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = UnitForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            create_unit(
                condominium=condominium,
                actor=request.user,
                block=form.cleaned_data["block"],
                number=form.cleaned_data["number"],
                floor=form.cleaned_data["floor"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Unidade cadastrada.")
            return redirect("core:unit_list")

    return render(request, "core/unit_form.html", {"form": form})


@login_required
def membership_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "core/membership_list.html",
        {"memberships": list_memberships_for_condominium(condominium=condominium)},
    )


@login_required
def membership_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = MembershipCreateForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            create_user_membership(
                condominium=condominium,
                actor=request.user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                username=form.cleaned_data["username"],
                temporary_password=form.cleaned_data["temporary_password"],
                role=form.cleaned_data["role"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Membro cadastrado.")
            return redirect("core:membership_list")

    return render(request, "core/membership_form.html", {"form": form})
