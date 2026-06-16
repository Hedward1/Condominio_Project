from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import AuditableModel, SoftDeleteModel


class ReservationStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    APPROVED = "APPROVED", "Aprovada"
    REJECTED = "REJECTED", "Rejeitada"
    CANCELLED = "CANCELLED", "Cancelada"


class Amenity(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="amenities",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    rules = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=Q(is_active=True),
                name="uniq_active_amenity_name_condo",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Reservation(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    amenity = models.ForeignKey(Amenity, on_delete=models.PROTECT, related_name="reservations")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=24,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    manager_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_reservations",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_reservations",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_at", "-created_at"]
        indexes = [
            models.Index(fields=["condominium", "status", "is_active"]),
            models.Index(fields=["condominium", "amenity", "start_at"]),
            models.Index(fields=["requested_by", "status"]),
        ]

    def clean(self):
        super().clean()
        if self.amenity_id and self.condominium_id and self.amenity.condominium_id != self.condominium_id:
            raise ValidationError({"amenity": "A area comum pertence a outro condominio."})
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "A data final deve ser maior que a inicial."})

    def __str__(self) -> str:
        return f"{self.amenity} - {self.requested_by} - {self.start_at:%Y-%m-%d %H:%M}"
