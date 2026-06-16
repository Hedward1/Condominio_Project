from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.reservation_list, name="reservation_list"),
    path("new/", views.reservation_create, name="reservation_create"),
    path("<uuid:reservation_id>/", views.reservation_detail, name="reservation_detail"),
    path("admin/reservations/", views.admin_reservation_list, name="admin_reservation_list"),
    path(
        "admin/reservations/<uuid:reservation_id>/",
        views.admin_reservation_detail,
        name="admin_reservation_detail",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/approve/",
        views.reservation_approve,
        name="reservation_approve",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/reject/",
        views.reservation_reject,
        name="reservation_reject",
    ),
    path(
        "admin/reservations/<uuid:reservation_id>/cancel/",
        views.reservation_cancel,
        name="reservation_cancel",
    ),
    path("admin/amenities/", views.amenity_list, name="amenity_list"),
    path("admin/amenities/new/", views.amenity_create, name="amenity_create"),
    path(
        "admin/amenities/<uuid:amenity_id>/edit/",
        views.amenity_update,
        name="amenity_update",
    ),
    path(
        "admin/amenities/<uuid:amenity_id>/deactivate/",
        views.amenity_deactivate,
        name="amenity_deactivate",
    ),
]
