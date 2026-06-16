from django.contrib import admin

from .models import Amenity, Reservation


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "condominium", "is_active")
    list_filter = ("condominium", "is_active")
    search_fields = ("name", "description", "rules", "condominium__name")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("amenity", "condominium", "requested_by", "start_at", "end_at", "status")
    list_filter = ("condominium", "status", "amenity", "is_active")
    search_fields = ("amenity__name", "requested_by__username", "notes", "manager_notes")
