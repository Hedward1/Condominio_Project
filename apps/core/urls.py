from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("select/", views.condominium_select, name="condominium_select"),
    path("blocks/", views.block_list, name="block_list"),
    path("blocks/new/", views.block_create, name="block_create"),
    path("units/", views.unit_list, name="unit_list"),
    path("units/new/", views.unit_create, name="unit_create"),
    path("memberships/", views.membership_list, name="membership_list"),
    path("memberships/new/", views.membership_create, name="membership_create"),
    path("occupancies/", views.unit_occupancy_list, name="unit_occupancy_list"),
    path("occupancies/new/", views.unit_occupancy_create, name="unit_occupancy_create"),
]
