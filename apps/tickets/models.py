from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import AuditableModel, BaseModel, SoftDeleteModel


class TicketStatus(models.TextChoices):
    OPEN = "OPEN", "Aberto"
    IN_PROGRESS = "IN_PROGRESS", "Em andamento"
    RESOLVED = "RESOLVED", "Resolvido"
    CLOSED = "CLOSED", "Fechado"


class TicketPriority(models.TextChoices):
    LOW = "LOW", "Baixa"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "Alta"
    URGENT = "URGENT", "Urgente"


class TicketCategory(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="ticket_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["condominium__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=Q(is_active=True),
                name="uniq_active_ticket_category_name_condo",
            ),
        ]
        indexes = [
            models.Index(fields=["condominium", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Ticket(AuditableModel, SoftDeleteModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    category = models.ForeignKey(
        TicketCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    unit = models.ForeignKey(
        "core.Unit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    title = models.CharField(max_length=180)
    description = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN,
        db_index=True,
    )
    priority = models.CharField(
        max_length=24,
        choices=TicketPriority.choices,
        default=TicketPriority.NORMAL,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
    )
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["condominium", "status", "is_active"]),
            models.Index(fields=["condominium", "priority", "is_active"]),
            models.Index(fields=["condominium", "created_at"]),
            models.Index(fields=["created_by", "is_active"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.category_id
            and self.condominium_id
            and self.category.condominium_id != self.condominium_id
        ):
            raise ValidationError({"category": "A categoria pertence a outro condominio."})
        if self.unit_id and self.condominium_id and self.unit.condominium_id != self.condominium_id:
            raise ValidationError({"unit": "A unidade pertence a outro condominio."})

    def __str__(self) -> str:
        return self.title


class TicketComment(BaseModel):
    condominium = models.ForeignKey(
        "core.Condominium",
        on_delete=models.PROTECT,
        related_name="ticket_comments",
    )
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_comments",
    )
    message = models.TextField()
    is_internal = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["condominium", "ticket", "created_at"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["condominium", "is_internal"]),
        ]

    def clean(self):
        super().clean()
        if self.ticket_id and self.condominium_id and self.ticket.condominium_id != self.condominium_id:
            raise ValidationError({"ticket": "O chamado pertence a outro condominio."})

    def __str__(self) -> str:
        return f"{self.author} - {self.ticket}"
