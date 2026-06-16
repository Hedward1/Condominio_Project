from django.http import Http404

from .models import Announcement, AnnouncementCategory, AnnouncementReadReceipt, AnnouncementStatus


def list_categories_for_condominium(*, condominium):
    return AnnouncementCategory.active_objects.filter(condominium=condominium).order_by("name")


def list_admin_announcements_for_condominium(*, condominium):
    return (
        Announcement.active_objects.filter(condominium=condominium)
        .select_related("category", "created_by", "published_by")
        .order_by("-is_pinned", "-created_at")
    )


def list_published_announcements_for_condominium(*, condominium):
    return (
        Announcement.active_objects.filter(
            condominium=condominium,
            status=AnnouncementStatus.PUBLISHED,
        )
        .select_related("category", "published_by")
        .order_by("-is_pinned", "-published_at", "-created_at")
    )


def get_announcement_for_condominium(*, condominium, announcement_id):
    announcement = (
        Announcement.active_objects.select_related("category", "created_by", "published_by")
        .filter(id=announcement_id, condominium=condominium)
        .first()
    )
    if announcement is None:
        raise Http404("Comunicado nao encontrado.")
    return announcement


def get_draft_announcement_for_condominium(*, condominium, announcement_id):
    announcement = (
        Announcement.active_objects.select_related("category")
        .filter(
            id=announcement_id,
            condominium=condominium,
            status=AnnouncementStatus.DRAFT,
        )
        .first()
    )
    if announcement is None:
        raise Http404("Rascunho nao encontrado.")
    return announcement


def get_published_announcement_for_condominium(*, condominium, announcement_id):
    announcement = (
        Announcement.active_objects.select_related("category", "published_by")
        .filter(
            id=announcement_id,
            condominium=condominium,
            status=AnnouncementStatus.PUBLISHED,
        )
        .first()
    )
    if announcement is None:
        raise Http404("Comunicado nao encontrado.")
    return announcement


def has_user_read_announcement(*, condominium, announcement, user) -> bool:
    return AnnouncementReadReceipt.objects.filter(
        condominium=condominium,
        announcement=announcement,
        user=user,
    ).exists()
