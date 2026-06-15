from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from .selectors import list_condominiums_for_user
from .services import set_active_condominium_for_request


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
