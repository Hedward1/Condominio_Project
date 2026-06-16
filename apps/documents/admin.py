from django.contrib import admin

from .models import Document, DocumentCategory


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "condominium", "is_active")
    list_filter = ("condominium", "is_active")
    search_fields = ("name", "description", "condominium__name")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "condominium", "visibility", "category", "is_active")
    list_filter = ("condominium", "visibility", "category", "is_active")
    search_fields = ("title", "description", "original_filename", "condominium__name")
