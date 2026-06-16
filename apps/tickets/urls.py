from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("new/", views.ticket_create, name="ticket_create"),
    path("<uuid:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("admin/tickets/", views.admin_ticket_list, name="admin_ticket_list"),
    path("admin/tickets/<uuid:ticket_id>/", views.admin_ticket_detail, name="admin_ticket_detail"),
    path("admin/categories/", views.category_list, name="category_list"),
    path("admin/categories/new/", views.category_create, name="category_create"),
    path(
        "admin/categories/<uuid:category_id>/edit/",
        views.category_update,
        name="category_update",
    ),
    path(
        "admin/categories/<uuid:category_id>/deactivate/",
        views.category_deactivate,
        name="category_deactivate",
    ),
]
