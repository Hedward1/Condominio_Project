from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import AuditableModel, SoftDeleteModel


class CondominiumRole(models.TextChoices):
    SUPERADMIN = "SUPERADMIN", "Superadmin"
    CONDO_ADMIN = "CONDO_ADMIN", "Admin do condominio"
    SYNDIC = "SYNDIC", "Sindico"
    COUNCIL = "COUNCIL", "Conselho"
    STAFF = "STAFF", "Funcionario"
    RESIDENT = "RESIDENT", "Morador"
    OWNER = "OWNER", "Proprietario"
    TENANT = "TENANT", "Inquilino"


class OccupancyType(models.TextChoices):
    OWNER = "OWNER", "Proprietario"
    TENANT = "TENANT", "Inquilino"
    RESIDENT = "RESIDENT", "Morador"
    DEPENDENT = "DEPENDENT", "Dependente"


class Condominium(AuditableModel, SoftDeleteModel):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    document_number = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=2, blank=True)
    postal_code = models.CharField(max_length=16, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Block(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="blocks")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=Q(is_active=True),
                name="uniq_active_block_name_condo",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.condominium} - {self.name}"


class Unit(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="units")
    block = models.ForeignKey(
        Block,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="units",
    )
    number = models.CharField(max_length=40)
    floor = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "block__name", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "block", "number"],
                condition=Q(is_active=True, block__isnull=False),
                name="uniq_active_unit_block_no",
            ),
            models.UniqueConstraint(
                fields=["condominium", "number"],
                condition=Q(is_active=True, block__isnull=True),
                name="uniq_active_unit_no_no_block",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
            models.Index(fields=["condominium", "block", "number"]),
        ]

    def clean(self):
        super().clean()
        if self.block_id and self.condominium_id and self.block.condominium_id != self.condominium_id:
            raise ValidationError({"block": "O bloco pertence a outro condominio."})

    def __str__(self) -> str:
        block = f"{self.block.name} " if self.block_id else ""
        return f"{block}{self.number}"


class CondominiumMembership(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        Condominium,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="condominium_memberships",
    )
    role = models.CharField(max_length=32, choices=CondominiumRole.choices)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_condominium_invites",
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["condominium__name", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "user"],
                condition=Q(is_active=True),
                name="uniq_active_member_condo_user",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "role", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.condominium} ({self.role})"


class UnitOccupancy(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        Condominium,
        on_delete=models.PROTECT,
        related_name="unit_occupancies",
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="occupancies")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unit_occupancies",
    )
    occupancy_type = models.CharField(max_length=32, choices=OccupancyType.choices)
    is_primary = models.BooleanField(default=False)
    starts_at = models.DateField(null=True, blank=True)
    ends_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["condominium__name", "unit__number", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "unit", "user", "occupancy_type"],
                condition=Q(is_active=True),
                name="uniq_active_occupancy_user_type",
            ),
            models.UniqueConstraint(
                fields=["condominium", "unit"],
                condition=Q(is_active=True, is_primary=True),
                name="uniq_active_primary_unit",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "unit", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.unit_id and self.condominium_id and self.unit.condominium_id != self.condominium_id:
            raise ValidationError({"unit": "A unidade pertence a outro condominio."})
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "A data final deve ser maior ou igual a inicial."})

    def __str__(self) -> str:
        return f"{self.user} - {self.unit}"


class CondominiumSettings(AuditableModel):
    condominium = models.OneToOneField(
        Condominium,
        on_delete=models.PROTECT,
        related_name="settings",
    )
    allow_council_view_all_tickets = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Condominium settings"

    def __str__(self) -> str:
        return f"Settings - {self.condominium}"
