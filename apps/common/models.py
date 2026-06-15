import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditableModel(BaseModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def soft_delete(self, *, user=None):
        return self.update(is_active=False, deleted_at=timezone.now(), deleted_by=user)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class ActiveSoftDeleteManager(SoftDeleteManager):
    def get_queryset(self):
        return super().get_queryset().active()


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = SoftDeleteManager()
    active_objects = ActiveSoftDeleteManager()

    class Meta:
        abstract = True

    def soft_delete(self, *, user=None, save=True):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.deleted_by = user
        if save:
            self.save(update_fields=["is_active", "deleted_at", "deleted_by", "updated_at"])
        return self
