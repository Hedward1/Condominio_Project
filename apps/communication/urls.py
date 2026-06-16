from django.urls import path

from . import views

app_name = "communication"

urlpatterns = [
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
