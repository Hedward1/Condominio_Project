from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "condominium", "actor", "action", "object_model", "object_id")
    list_filter = ("action", "object_app", "object_model", "created_at")
    search_fields = ("action", "object_repr", "object_id", "actor__username", "condominium__name")
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
