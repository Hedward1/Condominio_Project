from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("<uuid:document_id>/", views.document_detail, name="document_detail"),
    path("<uuid:document_id>/download/", views.document_download, name="document_download"),
    path("admin/documents/", views.admin_document_list, name="admin_document_list"),
    path("admin/documents/new/", views.document_create, name="document_create"),
    path("admin/documents/<uuid:document_id>/edit/", views.document_edit, name="document_edit"),
    path(
        "admin/documents/<uuid:document_id>/deactivate/",
        views.document_deactivate,
        name="document_deactivate",
    ),
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
