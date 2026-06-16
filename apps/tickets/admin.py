from django.contrib import admin

from .models import Ticket, TicketCategory, TicketComment


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "condominium", "is_active")
    list_filter = ("condominium", "is_active")
    search_fields = ("name", "description", "condominium__name")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "condominium", "status", "priority", "created_by", "assigned_to", "is_active")
    list_filter = ("condominium", "status", "priority", "is_active")
    search_fields = ("title", "description", "created_by__username", "assigned_to__username")


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "condominium", "is_internal", "created_at")
    list_filter = ("condominium", "is_internal")
    search_fields = ("ticket__title", "author__username", "message")
