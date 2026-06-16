import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Condominium, CondominiumMembership, CondominiumRole
from apps.dashboard.selectors import get_syndic_dashboard_summary
from apps.documents.models import Document, DocumentCategory, DocumentVisibility
from apps.documents.selectors import (
    get_document_for_resident,
    list_documents_for_manager,
    list_documents_for_resident,
)
from apps.documents.services import (
    create_document,
    deactivate_document,
    update_document_category,
    update_document_metadata,
)


def activate_condominium(client, condominium):
    session = client.session
    session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    session.save()


def make_uploaded_file(name="documento.pdf", content=b"arquivo", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def streaming_content(response):
    return b"".join(response.streaming_content)


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def documents_context(db, user_factory):
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    syndic = user_factory(username="syndic", email="syndic@example.com")
    resident = user_factory(username="resident", email="resident@example.com")
    other_resident = user_factory(username="other", email="other@example.com")
    for user, condo, role in (
        (syndic, condo_a, CondominiumRole.SYNDIC),
        (resident, condo_a, CondominiumRole.RESIDENT),
        (other_resident, condo_b, CondominiumRole.RESIDENT),
    ):
        CondominiumMembership.objects.create(condominium=condo, user=user, role=role)
    category_a = DocumentCategory.objects.create(condominium=condo_a, name="Atas")
    category_b = DocumentCategory.objects.create(condominium=condo_b, name="Outro condominio")
    return {
        "condo_a": condo_a,
        "condo_b": condo_b,
        "syndic": syndic,
        "resident": resident,
        "other_resident": other_resident,
        "category_a": category_a,
        "category_b": category_b,
    }


def make_document(
    *,
    condominium,
    created_by,
    title="Documento",
    category=None,
    visibility=DocumentVisibility.PUBLIC_TO_RESIDENTS,
    filename="documento.pdf",
    content=b"conteudo",
    is_active=True,
):
    document = Document.objects.create(
        condominium=condominium,
        category=category,
        title=title,
        description="Descricao do documento",
        file=make_uploaded_file(filename, content),
        original_filename=filename,
        file_size=len(content),
        content_type="application/pdf",
        visibility=visibility,
        created_by=created_by,
        updated_by=created_by,
    )
    if not is_active:
        document.soft_delete(user=created_by)
    return document


@pytest.mark.django_db
def test_resident_cannot_access_document_category_management(client, documents_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:category_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_resident_cannot_access_admin_document_list(client, documents_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:admin_document_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_creates_document_category_with_audit_log(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_create"),
        {"name": "Convencao", "description": "Documentos oficiais"},
    )

    assert response.status_code == 302
    category = DocumentCategory.objects.get(
        condominium=documents_context["condo_a"],
        name="Convencao",
    )
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document_category.created",
        object_id=str(category.id),
    ).exists()


@pytest.mark.django_db
def test_manager_updates_document_category_with_audit_log(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_update", args=[documents_context["category_a"].id]),
        {"name": "Atas de reuniao", "description": "Historico"},
    )

    assert response.status_code == 302
    documents_context["category_a"].refresh_from_db()
    assert documents_context["category_a"].name == "Atas de reuniao"
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document_category.updated",
        object_id=str(documents_context["category_a"].id),
    ).exists()


@pytest.mark.django_db
def test_manager_deactivates_document_category_with_audit_log(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_deactivate", args=[documents_context["category_a"].id]),
    )

    assert response.status_code == 302
    documents_context["category_a"].refresh_from_db()
    assert documents_context["category_a"].is_active is False
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document_category.deactivated",
        object_id=str(documents_context["category_a"].id),
    ).exists()


@pytest.mark.django_db
def test_duplicate_active_document_category_is_rejected(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_create"),
        {"name": "atas", "description": "Duplicada"},
    )

    assert response.status_code == 200
    assert DocumentCategory.active_objects.filter(
        condominium=documents_context["condo_a"],
        name__iexact="Atas",
    ).count() == 1


@pytest.mark.django_db
def test_other_condominium_category_is_not_accessible(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    list_response = client.get(reverse("documents:category_list"))
    update_response = client.get(
        reverse("documents:category_update", args=[documents_context["category_b"].id]),
    )
    deactivate_response = client.get(
        reverse("documents:category_deactivate", args=[documents_context["category_b"].id]),
    )

    assert list_response.status_code == 200
    assert b"Outro condominio" not in list_response.content
    assert update_response.status_code == 404
    assert deactivate_response.status_code == 404


@pytest.mark.django_db
def test_document_category_with_active_document_cannot_be_deactivated(
    client,
    documents_context,
):
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        category=documents_context["category_a"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_deactivate", args=[documents_context["category_a"].id]),
    )

    assert response.status_code == 200
    documents_context["category_a"].refresh_from_db()
    assert documents_context["category_a"].is_active is True
    assert not AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        action="documents.document_category.deactivated",
        object_id=str(documents_context["category_a"].id),
    ).exists()


@pytest.mark.django_db
def test_inactive_document_does_not_block_category_deactivation(client, documents_context):
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        category=documents_context["category_a"],
        is_active=False,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:category_deactivate", args=[documents_context["category_a"].id]),
    )

    assert response.status_code == 302
    documents_context["category_a"].refresh_from_db()
    assert documents_context["category_a"].is_active is False


@pytest.mark.django_db
def test_category_from_other_condominium_is_rejected_on_document_create(
    client,
    documents_context,
):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:document_create"),
        {
            "category": str(documents_context["category_b"].id),
            "title": "Documento invalido",
            "description": "Nao deve salvar",
            "visibility": DocumentVisibility.PUBLIC_TO_RESIDENTS,
            "file": make_uploaded_file(),
        },
    )

    assert response.status_code == 200
    assert not Document.objects.filter(
        condominium=documents_context["condo_a"],
        title="Documento invalido",
    ).exists()


@pytest.mark.django_db
def test_manager_creates_document_upload_with_audit_log(client, documents_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:document_create"),
        {
            "category": str(documents_context["category_a"].id),
            "title": "Regimento interno",
            "description": "Arquivo do regimento",
            "visibility": DocumentVisibility.PUBLIC_TO_RESIDENTS,
            "file": make_uploaded_file("regimento interno.pdf", b"regimento"),
        },
    )

    assert response.status_code == 302
    document = Document.objects.get(
        condominium=documents_context["condo_a"],
        title="Regimento interno",
    )
    assert document.original_filename == "regimento interno.pdf"
    assert document.file_size == len(b"regimento")
    assert document.content_type == "application/pdf"
    assert document.file.name.startswith(f"documents/{documents_context['condo_a'].id}/{document.id}/")
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document.created",
        object_id=str(document.id),
    ).exists()


@pytest.mark.django_db
def test_manager_updates_document_metadata_with_audit_log(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        category=documents_context["category_a"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:document_edit", args=[document.id]),
        {
            "category": "",
            "title": "Documento atualizado",
            "description": "Nova descricao",
            "visibility": DocumentVisibility.MANAGERS_ONLY,
        },
    )

    assert response.status_code == 302
    document.refresh_from_db()
    assert document.title == "Documento atualizado"
    assert document.category is None
    assert document.visibility == DocumentVisibility.MANAGERS_ONLY
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document.updated",
        object_id=str(document.id),
    ).exists()


@pytest.mark.django_db
def test_manager_cannot_update_document_to_other_condominium_category(
    client,
    documents_context,
):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        category=documents_context["category_a"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(
        reverse("documents:document_edit", args=[document.id]),
        {
            "category": str(documents_context["category_b"].id),
            "title": "Tentativa invalida",
            "description": "Nao deve salvar",
            "visibility": DocumentVisibility.PUBLIC_TO_RESIDENTS,
        },
    )

    assert response.status_code == 200
    document.refresh_from_db()
    assert document.category == documents_context["category_a"]
    assert document.title != "Tentativa invalida"


@pytest.mark.django_db
def test_manager_deactivates_document_with_audit_log(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.post(reverse("documents:document_deactivate", args=[document.id]))

    assert response.status_code == 302
    document.refresh_from_db()
    assert document.is_active is False
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document.deactivated",
        object_id=str(document.id),
    ).exists()


@pytest.mark.django_db
def test_resident_sees_only_public_documents_from_active_condominium(
    client,
    documents_context,
):
    public_document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Documento publico",
    )
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Documento restrito",
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
        title="Documento outro condominio",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:document_list"))

    assert response.status_code == 200
    assert public_document.title.encode() in response.content
    assert b"Documento restrito" not in response.content
    assert b"Documento outro condominio" not in response.content


@pytest.mark.django_db
def test_resident_cannot_view_or_download_managers_only_document(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    detail_response = client.get(reverse("documents:document_detail", args=[document.id]))
    download_response = client.get(reverse("documents:document_download", args=[document.id]))

    assert detail_response.status_code == 404
    assert download_response.status_code == 404


@pytest.mark.django_db
def test_resident_cannot_access_other_condominium_document(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
        title="Documento externo",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    detail_response = client.get(reverse("documents:document_detail", args=[document.id]))
    download_response = client.get(reverse("documents:document_download", args=[document.id]))

    assert detail_response.status_code == 404
    assert download_response.status_code == 404


@pytest.mark.django_db
def test_manager_sees_active_documents_from_active_condominium(client, documents_context):
    public_document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Documento publico",
    )
    managers_only_document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Documento restrito",
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
        title="Documento outro condominio",
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:admin_document_list"))

    assert response.status_code == 200
    assert public_document.title.encode() in response.content
    assert managers_only_document.title.encode() in response.content
    assert b"Documento outro condominio" not in response.content


@pytest.mark.django_db
def test_resident_downloads_public_document_through_protected_view(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        filename="publico.pdf",
        content=b"conteudo publico",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:document_download", args=[document.id]))

    assert response.status_code == 200
    assert streaming_content(response) == b"conteudo publico"
    assert "publico.pdf" in response.headers["Content-Disposition"]


@pytest.mark.django_db
def test_manager_downloads_managers_only_document_with_audit_log(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        filename="restrito.pdf",
        content=b"restrito",
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    response = client.get(reverse("documents:document_download", args=[document.id]))

    assert response.status_code == 200
    assert streaming_content(response) == b"restrito"
    assert AuditLog.objects.filter(
        condominium=documents_context["condo_a"],
        actor=documents_context["syndic"],
        action="documents.document.downloaded",
        object_id=str(document.id),
    ).exists()


@pytest.mark.django_db
def test_document_pages_do_not_expose_direct_media_url(client, documents_context):
    document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        filename="publico.pdf",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])

    list_response = client.get(reverse("documents:document_list"))
    detail_response = client.get(reverse("documents:document_detail", args=[document.id]))
    download_path = reverse("documents:document_download", args=[document.id])

    client.logout()
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, documents_context["condo_a"])
    admin_response = client.get(reverse("documents:admin_document_list"))

    for response in (list_response, detail_response, admin_response):
        assert response.status_code == 200
        assert document.file.url.encode() not in response.content
        assert download_path.encode() in response.content


@pytest.mark.django_db
def test_document_selectors_filter_by_condominium_and_visibility(documents_context):
    public_document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Publico A",
    )
    managers_only_document = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        title="Restrito A",
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
        title="Publico B",
    )

    manager_documents = list(
        list_documents_for_manager(condominium=documents_context["condo_a"]),
    )
    resident_documents = list(
        list_documents_for_resident(condominium=documents_context["condo_a"]),
    )

    assert set(manager_documents) == {public_document, managers_only_document}
    assert resident_documents == [public_document]
    with pytest.raises(Http404):
        get_document_for_resident(
            condominium=documents_context["condo_a"],
            document_id=managers_only_document.id,
        )


@pytest.mark.django_db
def test_document_services_block_cross_tenant_actions(documents_context):
    document_a = make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
    )
    document_b = make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
    )

    with pytest.raises(ValidationError):
        create_document(
            condominium=documents_context["condo_a"],
            actor=documents_context["syndic"],
            category=documents_context["category_b"],
            title="Documento cruzado",
            uploaded_file=make_uploaded_file(),
        )

    with pytest.raises(ValidationError):
        update_document_category(
            condominium=documents_context["condo_a"],
            actor=documents_context["syndic"],
            category=documents_context["category_b"],
            name="Categoria cruzada",
        )

    with pytest.raises(ValidationError):
        update_document_metadata(
            condominium=documents_context["condo_a"],
            actor=documents_context["syndic"],
            document=document_a,
            category=documents_context["category_b"],
            title="Categoria cruzada",
        )

    with pytest.raises(ValidationError):
        update_document_metadata(
            condominium=documents_context["condo_a"],
            actor=documents_context["syndic"],
            document=document_b,
            title="Documento cruzado",
        )

    with pytest.raises(ValidationError):
        deactivate_document(
            condominium=documents_context["condo_a"],
            actor=documents_context["syndic"],
            document=document_b,
        )


@pytest.mark.django_db
def test_dashboard_document_indicator_is_zero_without_documents(documents_context):
    summary = get_syndic_dashboard_summary(condominium=documents_context["condo_a"])

    assert summary["active_documents"] == 0


@pytest.mark.django_db
def test_dashboard_counts_active_documents_only_for_active_condominium(documents_context):
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
    )
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        visibility=DocumentVisibility.MANAGERS_ONLY,
    )
    make_document(
        condominium=documents_context["condo_a"],
        created_by=documents_context["syndic"],
        is_active=False,
    )
    make_document(
        condominium=documents_context["condo_b"],
        created_by=documents_context["other_resident"],
    )

    summary = get_syndic_dashboard_summary(condominium=documents_context["condo_a"])

    assert summary["active_documents"] == 2
