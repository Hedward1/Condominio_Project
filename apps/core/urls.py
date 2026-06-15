from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("select/", views.condominium_select, name="condominium_select"),
]
