from django.http import Http404

from .models import Document, DocumentCategory, DocumentVisibility


def list_document_categories_for_condominium(*, condominium):
    return DocumentCategory.active_objects.filter(condominium=condominium).order_by("name")


def get_document_category_for_condominium(*, condominium, category_id):
    category = DocumentCategory.active_objects.filter(
        id=category_id,
        condominium=condominium,
    ).first()
    if category is None:
        raise Http404("Categoria de documento nao encontrada.")
    return category


def list_documents_for_manager(*, condominium, filters=None):
    filters = filters or {}
    documents = Document.active_objects.filter(condominium=condominium)
    if filters.get("visibility"):
        documents = documents.filter(visibility=filters["visibility"])
    if filters.get("category"):
        documents = documents.filter(category=filters["category"])
    return documents.select_related("category", "created_by").order_by("-created_at")


def list_documents_for_resident(*, condominium):
    return (
        Document.active_objects.filter(
            condominium=condominium,
            visibility=DocumentVisibility.PUBLIC_TO_RESIDENTS,
        )
        .select_related("category", "created_by")
        .order_by("-created_at")
    )


def get_document_for_manager(*, condominium, document_id):
    document = (
        Document.active_objects.select_related("category", "created_by")
        .filter(id=document_id, condominium=condominium)
        .first()
    )
    if document is None:
        raise Http404("Documento nao encontrado.")
    return document


def get_document_for_resident(*, condominium, document_id):
    document = (
        Document.active_objects.select_related("category", "created_by")
        .filter(
            id=document_id,
            condominium=condominium,
            visibility=DocumentVisibility.PUBLIC_TO_RESIDENTS,
        )
        .first()
    )
    if document is None:
        raise Http404("Documento nao encontrado.")
    return document
