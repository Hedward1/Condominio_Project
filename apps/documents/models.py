from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import get_valid_filename

from apps.common.models import AuditableModel, SoftDeleteModel


class DocumentVisibility(models.TextChoices):
    PUBLIC_TO_RESIDENTS = "PUBLIC_TO_RESIDENTS", "Publico para moradores"
    MANAGERS_ONLY = "MANAGERS_ONLY", "Somente gestores"


def document_upload_to(instance, filename: str) -> str:
    safe_filename = get_valid_filename(Path(filename).name)
    return f"documents/{instance.condominium_id}/{instance.id}/{safe_filename}"


class DocumentCategory(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="document_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=Q(is_active=True),
                name="uniq_active_document_category_name_condo",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Document(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="documents",
    )
    category = models.ForeignKey(
        DocumentCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_to)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    visibility = models.CharField(
        max_length=32,
        choices=DocumentVisibility.choices,
        default=DocumentVisibility.PUBLIC_TO_RESIDENTS,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["condominium", "visibility", "is_active"]),
            models.Index(fields=["condominium", "created_at"]),
            models.Index(fields=["created_by", "is_active"]),
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
