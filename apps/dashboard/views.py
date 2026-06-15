from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .selectors import get_syndic_dashboard_summary


@login_required
def home(request):
    if request.condominium is None:
        return redirect("core:condominium_select")

    summary = get_syndic_dashboard_summary(condominium=request.condominium)
    return render(
        request,
        "dashboard/home.html",
        {"summary": summary},
    )
