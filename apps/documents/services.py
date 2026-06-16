from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import create_audit_log
from apps.core.permissions import require_condominium_manager

from .models import Document, DocumentCategory, DocumentVisibility


def _validate_category_condominium(*, condominium, category: DocumentCategory | None):
    if category is not None and category.condominium_id != condominium.id:
        raise ValidationError({"category": "A categoria pertence a outro condominio."})


def _validate_document_condominium(*, condominium, document: Document):
    if document.condominium_id != condominium.id:
        raise ValidationError({"document": "O documento pertence a outro condominio."})


def _validate_unique_active_category_name(
    *,
    condominium,
    name: str,
    category: DocumentCategory | None = None,
):
    duplicate_query = DocumentCategory.active_objects.filter(
        condominium=condominium,
        name__iexact=name.strip(),
    )
    if category is not None:
        duplicate_query = duplicate_query.exclude(id=category.id)
    if duplicate_query.exists():
        raise ValidationError({"name": "Ja existe uma categoria ativa com este nome."})


@transaction.atomic
def create_document_category(
    *,
    condominium,
    actor,
    name: str,
    description: str = "",
) -> DocumentCategory:
    require_condominium_manager(actor, condominium)
    _validate_unique_active_category_name(condominium=condominium, name=name)

    category = DocumentCategory(
        condominium=condominium,
        name=name.strip(),
        description=description,
        created_by=actor,
        updated_by=actor,
    )
    category.full_clean()
    category.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document_category.created",
        target=category,
    )
    return category


@transaction.atomic
def update_document_category(
    *,
    condominium,
    actor,
    category: DocumentCategory,
    name: str,
    description: str = "",
) -> DocumentCategory:
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)
    _validate_unique_active_category_name(
        condominium=condominium,
        name=name,
        category=category,
    )

    changes = {
        "name": {"from": category.name, "to": name.strip()},
        "description": {"from": category.description, "to": description},
    }
    category.name = name.strip()
    category.description = description
    category.updated_by = actor
    category.full_clean()
    category.save(update_fields=["name", "description", "updated_by", "updated_at"])
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document_category.updated",
        target=category,
        changes=changes,
    )
    return category


@transaction.atomic
def deactivate_document_category(*, condominium, actor, category: DocumentCategory):
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)
    if Document.active_objects.filter(condominium=condominium, category=category).exists():
        raise ValidationError(
            {
                "category": (
                    "Esta categoria possui documentos ativos. "
                    "Reclassifique ou desative os documentos primeiro."
                ),
            },
        )

    category.soft_delete(user=actor)
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document_category.deactivated",
        target=category,
    )
    return category


@transaction.atomic
def create_document(
    *,
    condominium,
    actor,
    title: str,
    uploaded_file,
    description: str = "",
    category: DocumentCategory | None = None,
    visibility: DocumentVisibility | str = DocumentVisibility.PUBLIC_TO_RESIDENTS,
) -> Document:
    require_condominium_manager(actor, condominium)
    _validate_category_condominium(condominium=condominium, category=category)

    document = Document(
        condominium=condominium,
        category=category,
        title=title,
        description=description,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        file_size=getattr(uploaded_file, "size", 0) or 0,
        content_type=getattr(uploaded_file, "content_type", "") or "",
        visibility=visibility,
        created_by=actor,
        updated_by=actor,
    )
    document.full_clean()
    document.save()
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document.created",
        target=document,
    )
    return document


@transaction.atomic
def update_document_metadata(
    *,
    condominium,
    actor,
    document: Document,
    title: str,
    description: str = "",
    category: DocumentCategory | None = None,
    visibility: DocumentVisibility | str = DocumentVisibility.PUBLIC_TO_RESIDENTS,
) -> Document:
    require_condominium_manager(actor, condominium)
    _validate_document_condominium(condominium=condominium, document=document)
    _validate_category_condominium(condominium=condominium, category=category)

    changes = {
        "category_id": {
            "from": str(document.category_id or ""),
            "to": str(category.id if category else ""),
        },
        "title": {"from": document.title, "to": title},
        "description": {"from": document.description, "to": description},
        "visibility": {"from": document.visibility, "to": visibility},
    }
    document.category = category
    document.title = title
    document.description = description
    document.visibility = visibility
    document.updated_by = actor
    document.full_clean()
    document.save(
        update_fields=[
            "category",
            "title",
            "description",
            "visibility",
            "updated_by",
            "updated_at",
        ],
    )
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document.updated",
        target=document,
        changes=changes,
    )
    return document


@transaction.atomic
def deactivate_document(*, condominium, actor, document: Document) -> Document:
    require_condominium_manager(actor, condominium)
    _validate_document_condominium(condominium=condominium, document=document)

    document.soft_delete(user=actor)
    create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document.deactivated",
        target=document,
    )
    return document


def record_document_download(*, condominium, actor, document: Document, request=None):
    _validate_document_condominium(condominium=condominium, document=document)
    if document.visibility != DocumentVisibility.MANAGERS_ONLY:
        return None

    require_condominium_manager(actor, condominium)
    return create_audit_log(
        condominium=condominium,
        actor=actor,
        action="documents.document.downloaded",
        target=document,
        request=request,
    )
