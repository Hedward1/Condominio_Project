from django.contrib import admin

from .models import Announcement, AnnouncementCategory, AnnouncementReadReceipt


@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "condominium", "is_active")
    list_filter = ("condominium", "is_active")
    search_fields = ("name", "description", "condominium__name")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "condominium", "status", "is_pinned", "published_at", "is_active")
    list_filter = ("condominium", "status", "is_pinned", "is_active")
    search_fields = ("title", "content", "condominium__name")


@admin.register(AnnouncementReadReceipt)
class AnnouncementReadReceiptAdmin(admin.ModelAdmin):
    list_display = ("announcement", "user", "condominium", "read_at")
    list_filter = ("condominium", "read_at")
    search_fields = ("announcement__title", "user__username", "user__email", "condominium__name")
