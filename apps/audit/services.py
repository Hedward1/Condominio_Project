from __future__ import annotations

from django.contrib.auth.models import AnonymousUser

from .models import AuditLog


def _get_client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def create_audit_log(
    *,
    condominium,
    actor=None,
    action: str,
    target=None,
    changes: dict | None = None,
    metadata: dict | None = None,
    request=None,
) -> AuditLog:
    if isinstance(actor, AnonymousUser):
        actor = None

    object_app = ""
    object_model = ""
    object_id = ""
    object_repr = ""

    if target is not None:
        object_app = target._meta.app_label
        object_model = target._meta.model_name
        object_id = str(target.pk)
        object_repr = str(target)[:255]

    return AuditLog.objects.create(
        condominium=condominium,
        actor=actor,
        action=action,
        object_app=object_app,
        object_model=object_model,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes or {},
        metadata=metadata or {},
        ip_address=_get_client_ip(request),
    )
