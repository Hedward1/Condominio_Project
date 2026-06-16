from django.urls import path

from . import views

app_name = "communication"

urlpatterns = [
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
    path("admin/announcements/", views.admin_announcement_list, name="admin_announcement_list"),
    path("admin/announcements/new/", views.announcement_create, name="announcement_create"),
    path(
        "admin/announcements/<uuid:announcement_id>/edit/",
        views.announcement_update,
        name="announcement_update",
    ),
    path(
        "admin/announcements/<uuid:announcement_id>/publish/",
        views.announcement_publish,
        name="announcement_publish",
    ),
    path(
        "admin/announcements/<uuid:announcement_id>/archive/",
        views.announcement_archive,
        name="announcement_archive",
    ),
    path("announcements/", views.mural, name="mural"),
    path("announcements/<uuid:announcement_id>/", views.announcement_detail, name="announcement_detail"),
    path(
        "announcements/<uuid:announcement_id>/read/",
        views.announcement_mark_read,
        name="announcement_mark_read",
    ),
]
