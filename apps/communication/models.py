from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditableModel, BaseModel, SoftDeleteModel


class AnnouncementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    PUBLISHED = "PUBLISHED", "Publicado"
    ARCHIVED = "ARCHIVED", "Arquivado"


class AnnouncementCategory(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="announcement_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=Q(is_active=True),
                name="uniq_active_announcement_category_name_condo",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Announcement(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="announcements",
    )
    category = models.ForeignKey(
        AnnouncementCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="announcements",
    )
    title = models.CharField(max_length=180)
    content = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=AnnouncementStatus.choices,
        default=AnnouncementStatus.DRAFT,
        db_index=True,
    )
    is_pinned = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_announcements",
    )

    class Meta:
        ordering = ["-is_pinned", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["condominium", "status", "is_active"]),
            models.Index(fields=["condominium", "published_at"]),
            models.Index(fields=["condominium", "is_pinned"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.category_id
            and self.condominium_id
            and self.category.condominium_id != self.condominium_id
        ):
            raise ValidationError({"category": "A categoria pertence a outro condominio."})

    def __str__(self) -> str:
        return self.title


class AnnouncementReadReceipt(BaseModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="announcement_read_receipts",
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.PROTECT,
        related_name="read_receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="announcement_read_receipts",
    )
    read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-read_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["announcement", "user"],
                name="uniq_announcement_read_receipt_user",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "read_at"]),
            models.Index(fields=["user", "read_at"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.announcement_id
            and self.condominium_id
            and self.announcement.condominium_id != self.condominium_id
        ):
            raise ValidationError(
                {"announcement": "O comunicado pertence a outro condominio."},
            )

    def __str__(self) -> str:
        return f"{self.user} leu {self.announcement}"
