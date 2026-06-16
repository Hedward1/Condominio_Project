from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("select/", views.condominium_select, name="condominium_select"),
    path("blocks/", views.block_list, name="block_list"),
    path("blocks/new/", views.block_create, name="block_create"),
    path("blocks/<uuid:block_id>/edit/", views.block_update, name="block_update"),
    path("blocks/<uuid:block_id>/deactivate/", views.block_deactivate, name="block_deactivate"),
    path("units/", views.unit_list, name="unit_list"),
    path("units/new/", views.unit_create, name="unit_create"),
    path("units/<uuid:unit_id>/edit/", views.unit_update, name="unit_update"),
    path("units/<uuid:unit_id>/deactivate/", views.unit_deactivate, name="unit_deactivate"),
    path("memberships/", views.membership_list, name="membership_list"),
    path("memberships/new/", views.membership_create, name="membership_create"),
    path(
        "memberships/<uuid:membership_id>/deactivate/",
        views.membership_deactivate,
        name="membership_deactivate",
    ),
    path("occupancies/", views.unit_occupancy_list, name="unit_occupancy_list"),
    path("occupancies/new/", views.unit_occupancy_create, name="unit_occupancy_create"),
    path(
        "occupancies/<uuid:occupancy_id>/deactivate/",
        views.unit_occupancy_deactivate,
        name="unit_occupancy_deactivate",
    ),
]
