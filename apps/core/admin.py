from django.contrib import admin

from .models import (
    Block,
    Condominium,
    CondominiumMembership,
    CondominiumSettings,
    Unit,
    UnitOccupancy,
)


@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "city", "state", "is_active")
    list_filter = ("is_active", "state")
    search_fields = ("name", "slug", "document_number", "city")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("name", "condominium", "is_active")
    list_filter = ("condominium", "is_active")
    search_fields = ("name", "condominium__name")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("number", "block", "condominium", "floor", "is_active")
    list_filter = ("condominium", "block", "is_active")
    search_fields = ("number", "block__name", "condominium__name")


@admin.register(CondominiumMembership)
class CondominiumMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "condominium", "role", "is_active", "joined_at")
    list_filter = ("role", "condominium", "is_active")
    search_fields = ("user__username", "user__email", "condominium__name")


@admin.register(UnitOccupancy)
class UnitOccupancyAdmin(admin.ModelAdmin):
    list_display = ("user", "unit", "condominium", "occupancy_type", "is_primary", "is_active")
    list_filter = ("occupancy_type", "condominium", "is_active")
    search_fields = ("user__username", "user__email", "unit__number", "condominium__name")


@admin.register(CondominiumSettings)
class CondominiumSettingsAdmin(admin.ModelAdmin):
    list_display = ("condominium", "created_at", "updated_at")
    search_fields = ("condominium__name",)
