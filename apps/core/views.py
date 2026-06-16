from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from .forms import BlockForm, MembershipCreateForm, UnitForm, UnitOccupancyForm
from .permissions import require_condominium_manager
from .selectors import (
    get_block_for_condominium,
    get_membership_by_id_for_condominium,
    get_occupancy_for_condominium,
    get_unit_for_condominium,
    list_blocks_for_condominium,
    list_condominiums_for_user,
    list_memberships_for_condominium,
    list_occupancies_for_condominium,
    list_units_for_condominium,
)
from .services import (
    create_block,
    create_unit,
    create_unit_occupancy,
    create_user_membership,
    deactivate_block,
    deactivate_membership,
    deactivate_unit,
    deactivate_unit_occupancy,
    set_active_condominium_for_request,
    update_block,
    update_unit,
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


def _render_deactivate_confirmation(request, *, title, object_label, cancel_url_name):
    return render(
        request,
        "core/deactivate_confirm.html",
        {
            "title": title,
            "object_label": object_label,
            "cancel_url_name": cancel_url_name,
        },
    )


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
def block_update(request, block_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    block = get_block_for_condominium(condominium=condominium, block_id=block_id)

    form = BlockForm(
        request.POST or None,
        initial={"name": block.name, "description": block.description},
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_block(
                condominium=condominium,
                actor=request.user,
                block=block,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Bloco atualizado.")
            return redirect("core:block_list")

    return render(request, "core/block_form.html", {"form": form, "is_update": True})


@login_required
def block_deactivate(request, block_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    block = get_block_for_condominium(condominium=condominium, block_id=block_id)

    if request.method == "POST":
        try:
            deactivate_block(condominium=condominium, actor=request.user, block=block)
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Bloco desativado.")
            return redirect("core:block_list")

    return _render_deactivate_confirmation(
        request,
        title="Desativar bloco",
        object_label=block.name,
        cancel_url_name="core:block_list",
    )


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
def unit_update(request, unit_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    unit = get_unit_for_condominium(condominium=condominium, unit_id=unit_id)

    form = UnitForm(
        request.POST or None,
        condominium=condominium,
        initial={
            "block": unit.block_id,
            "number": unit.number,
            "floor": unit.floor,
            "description": unit.description,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_unit(
                condominium=condominium,
                actor=request.user,
                unit=unit,
                block=form.cleaned_data["block"],
                number=form.cleaned_data["number"],
                floor=form.cleaned_data["floor"],
                description=form.cleaned_data["description"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Unidade atualizada.")
            return redirect("core:unit_list")

    return render(request, "core/unit_form.html", {"form": form, "is_update": True})


@login_required
def unit_deactivate(request, unit_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    unit = get_unit_for_condominium(condominium=condominium, unit_id=unit_id)

    if request.method == "POST":
        try:
            deactivate_unit(condominium=condominium, actor=request.user, unit=unit)
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Unidade desativada.")
            return redirect("core:unit_list")

    return _render_deactivate_confirmation(
        request,
        title="Desativar unidade",
        object_label=str(unit),
        cancel_url_name="core:unit_list",
    )


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


@login_required
def membership_deactivate(request, membership_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    membership = get_membership_by_id_for_condominium(
        condominium=condominium,
        membership_id=membership_id,
    )

    if request.method == "POST":
        try:
            deactivate_membership(
                condominium=condominium,
                actor=request.user,
                membership=membership,
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Membro desativado.")
            return redirect("core:membership_list")

    return _render_deactivate_confirmation(
        request,
        title="Desativar membro",
        object_label=str(membership.user),
        cancel_url_name="core:membership_list",
    )


@login_required
def unit_occupancy_list(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    return render(
        request,
        "core/unit_occupancy_list.html",
        {"occupancies": list_occupancies_for_condominium(condominium=condominium)},
    )


@login_required
def unit_occupancy_create(request):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)

    form = UnitOccupancyForm(request.POST or None, condominium=condominium)
    if request.method == "POST" and form.is_valid():
        try:
            create_unit_occupancy(
                condominium=condominium,
                actor=request.user,
                unit=form.cleaned_data["unit"],
                user=form.cleaned_data["user"],
                occupancy_type=form.cleaned_data["occupancy_type"],
                is_primary=form.cleaned_data["is_primary"],
                starts_at=form.cleaned_data["starts_at"],
                ends_at=form.cleaned_data["ends_at"],
            )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Morador por unidade cadastrado.")
            return redirect("core:unit_occupancy_list")

    return render(request, "core/unit_occupancy_form.html", {"form": form})


@login_required
def unit_occupancy_deactivate(request, occupancy_id):
    condominium, response = _active_condominium_or_redirect(request)
    if response is not None:
        return response
    require_condominium_manager(request.user, condominium)
    occupancy = get_occupancy_for_condominium(
        condominium=condominium,
        occupancy_id=occupancy_id,
    )

    if request.method == "POST":
        try:
            deactivate_unit_occupancy(
                condominium=condominium,
                actor=request.user,
                occupancy=occupancy,
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Morador por unidade desativado.")
            return redirect("core:unit_occupancy_list")

    return _render_deactivate_confirmation(
        request,
        title="Desativar morador por unidade",
        object_label=str(occupancy),
        cancel_url_name="core:unit_occupancy_list",
    )
