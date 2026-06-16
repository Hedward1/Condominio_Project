import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.communication.models import (
    Announcement,
    AnnouncementCategory,
    AnnouncementReadReceipt,
    AnnouncementStatus,
)
from apps.communication.selectors import list_published_announcements_for_condominium
from apps.communication.services import create_announcement, publish_announcement
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Condominium, CondominiumMembership, CondominiumRole


def activate_condominium(client, condominium):
    session = client.session
    session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    session.save()


@pytest.fixture
def communication_context(db, user_factory):
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    syndic = user_factory(username="syndic", email="syndic@example.com")
    resident = user_factory(username="resident", email="resident@example.com")
    other_resident = user_factory(username="other", email="other@example.com")
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=syndic,
        role=CondominiumRole.SYNDIC,
    )
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=resident,
        role=CondominiumRole.RESIDENT,
    )
    CondominiumMembership.objects.create(
        condominium=condo_b,
        user=other_resident,
        role=CondominiumRole.RESIDENT,
    )
    return {
        "condo_a": condo_a,
        "condo_b": condo_b,
        "syndic": syndic,
        "resident": resident,
        "other_resident": other_resident,
    }


def create_published_announcement(*, condominium, title="Published Notice", actor=None):
    return Announcement.objects.create(
        condominium=condominium,
        title=title,
        content="Conteudo publicado",
        status=AnnouncementStatus.PUBLISHED,
        published_at=timezone.now(),
        published_by=actor,
        created_by=actor,
        updated_by=actor,
    )


@pytest.mark.django_db
def test_resident_cannot_access_announcement_admin(client, communication_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.get(reverse("communication:admin_announcement_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_syndic_creates_draft_announcement(client, communication_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.post(
        reverse("communication:announcement_create"),
        {
            "category": "",
            "title": "Water Notice",
            "content": "Water outage tomorrow.",
            "is_pinned": "on",
        },
    )

    assert response.status_code == 302
    announcement = Announcement.objects.get(
        condominium=communication_context["condo_a"],
        title="Water Notice",
    )
    assert announcement.status == AnnouncementStatus.DRAFT
    assert announcement.is_pinned is True
    assert announcement.created_by == communication_context["syndic"]


@pytest.mark.django_db
def test_syndic_edits_draft_announcement(client, communication_context):
    announcement = Announcement.objects.create(
        condominium=communication_context["condo_a"],
        title="Old Title",
        content="Old content",
        status=AnnouncementStatus.DRAFT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.post(
        reverse("communication:announcement_update", args=[announcement.id]),
        {
            "category": "",
            "title": "New Title",
            "content": "New content",
        },
    )

    assert response.status_code == 302
    announcement.refresh_from_db()
    assert announcement.title == "New Title"
    assert announcement.content == "New content"
    assert announcement.status == AnnouncementStatus.DRAFT


@pytest.mark.django_db
def test_syndic_publishes_announcement_with_audit_log(client, communication_context):
    announcement = Announcement.objects.create(
        condominium=communication_context["condo_a"],
        title="Draft Notice",
        content="Publish me",
        status=AnnouncementStatus.DRAFT,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.post(reverse("communication:announcement_publish", args=[announcement.id]))

    assert response.status_code == 302
    announcement.refresh_from_db()
    assert announcement.status == AnnouncementStatus.PUBLISHED
    assert announcement.published_at is not None
    assert announcement.published_by == communication_context["syndic"]
    assert AuditLog.objects.filter(
        condominium=communication_context["condo_a"],
        actor=communication_context["syndic"],
        action="communication.announcement.published",
        object_id=str(announcement.id),
    ).exists()


@pytest.mark.django_db
def test_syndic_archives_announcement_with_audit_log(client, communication_context):
    announcement = create_published_announcement(
        condominium=communication_context["condo_a"],
        actor=communication_context["syndic"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.post(reverse("communication:announcement_archive", args=[announcement.id]))

    assert response.status_code == 302
    announcement.refresh_from_db()
    assert announcement.status == AnnouncementStatus.ARCHIVED
    assert AuditLog.objects.filter(
        condominium=communication_context["condo_a"],
        actor=communication_context["syndic"],
        action="communication.announcement.archived",
        object_id=str(announcement.id),
    ).exists()


@pytest.mark.django_db
def test_resident_sees_published_announcement(client, communication_context):
    create_published_announcement(
        condominium=communication_context["condo_a"],
        title="Visible Notice",
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.get(reverse("communication:mural"))

    assert response.status_code == 200
    assert b"Visible Notice" in response.content


@pytest.mark.django_db
def test_resident_does_not_see_draft_announcement(client, communication_context):
    Announcement.objects.create(
        condominium=communication_context["condo_a"],
        title="Hidden Draft",
        content="Nao deve aparecer",
        status=AnnouncementStatus.DRAFT,
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.get(reverse("communication:mural"))

    assert response.status_code == 200
    assert b"Hidden Draft" not in response.content


@pytest.mark.django_db
def test_user_from_other_condominium_does_not_see_announcement(client, communication_context):
    announcement = create_published_announcement(
        condominium=communication_context["condo_a"],
        title="Private Condo A Notice",
    )
    client.login(username="other", password="testpass123")
    activate_condominium(client, communication_context["condo_b"])

    mural_response = client.get(reverse("communication:mural"))
    detail_response = client.get(
        reverse("communication:announcement_detail", args=[announcement.id]),
    )

    assert mural_response.status_code == 200
    assert b"Private Condo A Notice" not in mural_response.content
    assert detail_response.status_code == 404


@pytest.mark.django_db
def test_mark_as_read_creates_read_receipt(client, communication_context):
    announcement = create_published_announcement(condominium=communication_context["condo_a"])
    client.login(username="resident", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    response = client.post(reverse("communication:announcement_mark_read", args=[announcement.id]))

    assert response.status_code == 302
    assert AnnouncementReadReceipt.objects.filter(
        condominium=communication_context["condo_a"],
        announcement=announcement,
        user=communication_context["resident"],
    ).exists()


@pytest.mark.django_db
def test_mark_as_read_twice_does_not_duplicate_receipt(client, communication_context):
    announcement = create_published_announcement(condominium=communication_context["condo_a"])
    client.login(username="resident", password="testpass123")
    activate_condominium(client, communication_context["condo_a"])

    url = reverse("communication:announcement_mark_read", args=[announcement.id])
    client.post(url)
    client.post(url)

    assert AnnouncementReadReceipt.objects.filter(
        condominium=communication_context["condo_a"],
        announcement=announcement,
        user=communication_context["resident"],
    ).count() == 1


@pytest.mark.django_db
def test_announcement_selectors_filter_by_condominium(communication_context):
    announcement_a = create_published_announcement(
        condominium=communication_context["condo_a"],
        title="Condo A Notice",
    )
    create_published_announcement(
        condominium=communication_context["condo_b"],
        title="Condo B Notice",
    )

    announcements = list(list_published_announcements_for_condominium(
        condominium=communication_context["condo_a"],
    ))

    assert announcements == [announcement_a]


@pytest.mark.django_db
def test_announcement_services_block_cross_tenant_actions(communication_context):
    category_b = AnnouncementCategory.objects.create(
        condominium=communication_context["condo_b"],
        name="Condo B Category",
    )
    announcement_b = Announcement.objects.create(
        condominium=communication_context["condo_b"],
        title="Condo B Draft",
        content="Outro condominio",
        status=AnnouncementStatus.DRAFT,
    )

    with pytest.raises(ValidationError):
        create_announcement(
            condominium=communication_context["condo_a"],
            actor=communication_context["syndic"],
            title="Invalid Category",
            content="Nao deve salvar",
            category=category_b,
        )

    with pytest.raises(ValidationError):
        publish_announcement(
            condominium=communication_context["condo_a"],
            actor=communication_context["syndic"],
            announcement=announcement_b,
        )

    announcement_b.refresh_from_db()
    assert announcement_b.status == AnnouncementStatus.DRAFT
