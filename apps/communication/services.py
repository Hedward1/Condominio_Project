from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import create_audit_log
from apps.core.permissions import require_active_membership, require_condominium_manager

from .models import (
    Announcement,
    AnnouncementCategory,
    AnnouncementReadReceipt,
    AnnouncementStatus,
)


def _validate_announcement_condominium(*, condominium, announcement: Announcement):
    if announcement.condominium_id != condominium.id:
        raise ValidationError({"announcement": "O comunicado pertence a outro condominio."})


def _validate_category_condominium(
    *,
    condominium,
    category: AnnouncementCategory | None,
):
    if category is not None and category.condominium_id != condominium.id:
        raise ValidationError({"category": "A categoria pertence a outro condominio."})


@transaction.atomic
def create_announcement(
    *,
    condominium,
    actor,
    title: str,
    content: str,
    category: AnnouncementCategory | None = None,
    is_pinned: bool = False,
) -> Announcement:
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)

    announcement = Announcement(
        condominium=condominium,
        category=category,
        title=title,
        content=content,
        is_pinned=is_pinned,
        status=AnnouncementStatus.DRAFT,
        created_by=actor,
        updated_by=actor,
    )
    announcement.full_clean()
    announcement.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="communication.announcement.created",
        target=announcement,
    )
    return announcement


@transaction.atomic
def update_draft_announcement(
    *,
    condominium,
    actor,
    announcement: Announcement,
    title: str,
    content: str,
    category: AnnouncementCategory | None = None,
    is_pinned: bool = False,
) -> Announcement:
    require_condominium_manager(actor, condominium)
    _validate_announcement_condominium(condominium=condominium, announcement=announcement)
    _validate_category_condominium(condominium=condominium, category=category)
    if announcement.status != AnnouncementStatus.DRAFT:
        raise ValidationError(
            {"announcement": "Somente comunicados em rascunho podem ser editados."},
        )

    changes = {
        "category_id": {
            "from": str(announcement.category_id or ""),
            "to": str(category.id if category else ""),
        },
        "title": {"from": announcement.title, "to": title},
        "content": {"from": announcement.content, "to": content},
        "is_pinned": {"from": announcement.is_pinned, "to": is_pinned},
    }
    announcement.category = category
    announcement.title = title
    announcement.content = content
    announcement.is_pinned = is_pinned
    announcement.updated_by = actor
    announcement.full_clean()
    announcement.save(
        update_fields=[
            "category",
            "title",
            "content",
            "is_pinned",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="communication.announcement.updated",
        target=announcement,
        changes=changes,
    )
    return announcement


@transaction.atomic
def publish_announcement(*, condominium, actor, announcement: Announcement) -> Announcement:
    require_condominium_manager(actor, condominium)
    _validate_announcement_condominium(condominium=condominium, announcement=announcement)
    if announcement.status != AnnouncementStatus.DRAFT:
        raise ValidationError({"announcement": "Somente rascunhos podem ser publicados."})

    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.published_at = timezone.now()
    announcement.published_by = actor
    announcement.updated_by = actor
    announcement.full_clean()
    announcement.save(
        update_fields=[
            "status",
            "published_at",
            "published_by",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="communication.announcement.published",
        target=announcement,
    )
    return announcement


@transaction.atomic
def archive_announcement(*, condominium, actor, announcement: Announcement) -> Announcement:
    require_condominium_manager(actor, condominium)
    _validate_announcement_condominium(condominium=condominium, announcement=announcement)
    if announcement.status == AnnouncementStatus.ARCHIVED:
        raise ValidationError({"announcement": "Este comunicado ja esta arquivado."})

    announcement.status = AnnouncementStatus.ARCHIVED
    announcement.updated_by = actor
    announcement.full_clean()
    announcement.save(update_fields=["status", "updated_by", "updated_at"])
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="communication.announcement.archived",
        target=announcement,
    )
    return announcement


@transaction.atomic
def mark_announcement_as_read(*, condominium, user, announcement: Announcement):
    require_active_membership(user, condominium)
    _validate_announcement_condominium(condominium=condominium, announcement=announcement)
    if announcement.status != AnnouncementStatus.PUBLISHED:
        raise ValidationError({"announcement": "Somente comunicados publicados podem ser lidos."})

    try:
        with transaction.atomic():
            receipt, created = AnnouncementReadReceipt.objects.get_or_create(
                condominium=condominium,
                announcement=announcement,
                user=user,
            )
    except IntegrityError:
        receipt = AnnouncementReadReceipt.objects.get(
            condominium=condominium,
            announcement=announcement,
            user=user,
        )
        created = False

    if created:
        create_audit_log(
            condominium=condominium,
            actor=user,
            action="communication.announcement.read",
            target=announcement,
            metadata={"read_receipt_id": str(receipt.id)},
        )
    return receipt
