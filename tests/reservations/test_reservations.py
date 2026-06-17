from datetime import datetime, time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Condominium, CondominiumMembership, CondominiumRole
from apps.dashboard.selectors import get_syndic_dashboard_summary
from apps.reservations.models import Amenity, Reservation, ReservationStatus
from apps.reservations.selectors import (
    list_reservation_days_for_amenity,
    list_reservations_for_manager,
    list_reservations_for_user,
)
from apps.reservations.services import (
    approve_reservation,
    cancel_reservation,
    request_reservation,
    update_amenity,
)


def activate_condominium(client, condominium):
    session = client.session
    session[ACTIVE_CONDOMINIUM_SESSION_KEY] = str(condominium.id)
    session.save()


def datetime_input(value):
    return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")


def future_window(days=1, hours=0, duration_hours=2):
    start = timezone.now() + timedelta(days=days, hours=hours)
    end = start + timedelta(hours=duration_hours)
    return start, end


def future_month_window(day=10, hour=18, duration_hours=2):
    first_next_month = (timezone.localdate().replace(day=1) + timedelta(days=40)).replace(day=1)
    start_date = first_next_month.replace(day=day)
    start = timezone.make_aware(
        datetime.combine(start_date, time(hour=hour)),
        timezone.get_current_timezone(),
    )
    end = start + timedelta(hours=duration_hours)
    return start, end


@pytest.fixture
def reservations_context(db, user_factory):
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    syndic = user_factory(username="syndic", email="syndic@example.com")
    resident = user_factory(username="resident", email="resident@example.com")
    second_resident = user_factory(username="resident2", email="resident2@example.com")
    other_resident = user_factory(username="other", email="other@example.com")
    for user, condo, role in (
        (syndic, condo_a, CondominiumRole.SYNDIC),
        (resident, condo_a, CondominiumRole.RESIDENT),
        (second_resident, condo_a, CondominiumRole.RESIDENT),
        (other_resident, condo_b, CondominiumRole.RESIDENT),
    ):
        CondominiumMembership.objects.create(condominium=condo, user=user, role=role)
    amenity_a = Amenity.objects.create(
        condominium=condo_a,
        name="Salao de festas",
        description="Espaco para eventos",
        rules="Sem som alto apos 22h.",
    )
    amenity_b = Amenity.objects.create(condominium=condo_b, name="Churrasqueira")
    return {
        "condo_a": condo_a,
        "condo_b": condo_b,
        "syndic": syndic,
        "resident": resident,
        "second_resident": second_resident,
        "other_resident": other_resident,
        "amenity_a": amenity_a,
        "amenity_b": amenity_b,
    }


def make_reservation(
    *,
    condominium,
    amenity,
    requested_by,
    status=ReservationStatus.PENDING,
    days=1,
    hours=0,
    duration_hours=2,
):
    start_at, end_at = future_window(days=days, hours=hours, duration_hours=duration_hours)
    return Reservation.objects.create(
        condominium=condominium,
        amenity=amenity,
        requested_by=requested_by,
        start_at=start_at,
        end_at=end_at,
        status=status,
        created_by=requested_by,
        updated_by=requested_by,
    )


@pytest.mark.django_db
def test_resident_cannot_access_amenity_management(client, reservations_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:amenity_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_resident_cannot_access_admin_reservation_list(client, reservations_context):
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:admin_reservation_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_resident_lists_active_amenities(client, reservations_context):
    Amenity.objects.create(
        condominium=reservations_context["condo_a"],
        name="Piscina",
    ).soft_delete(user=reservations_context["syndic"])
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:reservation_list"))

    assert response.status_code == 200
    assert b"Salao de festas" in response.content
    assert b"Piscina" not in response.content


@pytest.mark.django_db
def test_manager_creates_amenity_with_audit_log(client, reservations_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_create"),
        {
            "name": "Academia",
            "description": "Espaco fitness",
            "rules": "Uso das 6h as 22h.",
        },
    )

    assert response.status_code == 302
    amenity = Amenity.objects.get(condominium=reservations_context["condo_a"], name="Academia")
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.amenity.created",
        object_id=str(amenity.id),
    ).exists()


@pytest.mark.django_db
def test_manager_updates_amenity_with_audit_log(client, reservations_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_update", args=[reservations_context["amenity_a"].id]),
        {
            "name": "Salao atualizado",
            "description": "Nova descricao",
            "rules": "Novas regras",
        },
    )

    assert response.status_code == 302
    reservations_context["amenity_a"].refresh_from_db()
    assert reservations_context["amenity_a"].name == "Salao atualizado"
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.amenity.updated",
        object_id=str(reservations_context["amenity_a"].id),
    ).exists()


@pytest.mark.django_db
def test_manager_deactivates_amenity_with_audit_log(client, reservations_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_deactivate", args=[reservations_context["amenity_a"].id]),
    )

    assert response.status_code == 302
    reservations_context["amenity_a"].refresh_from_db()
    assert reservations_context["amenity_a"].is_active is False
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.amenity.deactivated",
        object_id=str(reservations_context["amenity_a"].id),
    ).exists()


@pytest.mark.django_db
def test_duplicate_active_amenity_is_rejected(client, reservations_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_create"),
        {"name": "salao de festas", "description": "Duplicado", "rules": ""},
    )

    assert response.status_code == 200
    assert Amenity.active_objects.filter(
        condominium=reservations_context["condo_a"],
        name__iexact="Salao de festas",
    ).count() == 1


@pytest.mark.django_db
def test_other_condominium_amenity_is_not_accessible(client, reservations_context):
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    list_response = client.get(reverse("reservations:amenity_list"))
    update_response = client.get(
        reverse("reservations:amenity_update", args=[reservations_context["amenity_b"].id]),
    )
    deactivate_response = client.get(
        reverse("reservations:amenity_deactivate", args=[reservations_context["amenity_b"].id]),
    )

    assert list_response.status_code == 200
    assert b"Churrasqueira" not in list_response.content
    assert update_response.status_code == 404
    assert deactivate_response.status_code == 404


@pytest.mark.django_db
def test_amenity_with_open_reservation_cannot_be_deactivated(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_deactivate", args=[reservations_context["amenity_a"].id]),
    )

    assert response.status_code == 200
    reservations_context["amenity_a"].refresh_from_db()
    assert reservations_context["amenity_a"].is_active is True
    assert reservation.is_active is True
    assert not AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        action="reservations.amenity.deactivated",
        object_id=str(reservations_context["amenity_a"].id),
    ).exists()


@pytest.mark.django_db
def test_amenity_with_only_closed_reservations_can_be_deactivated(client, reservations_context):
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.REJECTED,
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.CANCELLED,
        days=2,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:amenity_deactivate", args=[reservations_context["amenity_a"].id]),
    )

    assert response.status_code == 302
    reservations_context["amenity_a"].refresh_from_db()
    assert reservations_context["amenity_a"].is_active is False


@pytest.mark.django_db
def test_resident_requests_reservation_with_audit_log(client, reservations_context):
    start_at, end_at = future_window()
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "start_at": datetime_input(start_at),
            "end_at": datetime_input(end_at),
            "notes": "Aniversario",
        },
    )

    assert response.status_code == 302
    reservation = Reservation.objects.get(
        condominium=reservations_context["condo_a"],
        requested_by=reservations_context["resident"],
    )
    assert reservation.status == ReservationStatus.PENDING
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["resident"],
        action="reservations.reservation.requested",
        object_id=str(reservation.id),
    ).exists()


@pytest.mark.django_db
def test_reservation_create_shows_availability_for_selected_amenity(
    client,
    reservations_context,
):
    approved_start, approved_end = future_month_window(day=10, hour=18)
    pending_start, pending_end = future_month_window(day=11, hour=9, duration_hours=3)
    Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        start_at=approved_start,
        end_at=approved_end,
        status=ReservationStatus.APPROVED,
    )
    Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        start_at=pending_start,
        end_at=pending_end,
        status=ReservationStatus.PENDING,
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "month": approved_start.strftime("%Y-%m"),
        },
    )

    assert response.status_code == 200
    assert b"Disponibilidade da area" in response.content
    assert b"Com reserva" in response.content
    assert b"Pendente" in response.content
    assert b"Livre" in response.content
    assert b"18:00 as 20:00" in response.content
    assert b"09:00 as 12:00" in response.content
    days_by_day = {day["day"]: day for day in response.context["availability"]["days"]}
    assert days_by_day[10]["label"] == "Com reserva"
    assert days_by_day[11]["label"] == "Pendente"
    assert days_by_day[12]["label"] == "Livre"


@pytest.mark.django_db
def test_reservation_availability_ignores_other_amenity_condominium_and_closed_statuses(
    client,
    reservations_context,
):
    target_start, target_end = future_month_window(day=10, hour=18)
    other_amenity = Amenity.objects.create(
        condominium=reservations_context["condo_a"],
        name="Piscina",
    )
    Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=other_amenity,
        requested_by=reservations_context["resident"],
        start_at=target_start,
        end_at=target_end,
        status=ReservationStatus.APPROVED,
    )
    Reservation.objects.create(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
        start_at=target_start,
        end_at=target_end,
        status=ReservationStatus.APPROVED,
    )
    for status in (ReservationStatus.REJECTED, ReservationStatus.CANCELLED):
        Reservation.objects.create(
            condominium=reservations_context["condo_a"],
            amenity=reservations_context["amenity_a"],
            requested_by=reservations_context["resident"],
            start_at=target_start,
            end_at=target_end,
            status=status,
        )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "month": target_start.strftime("%Y-%m"),
        },
    )

    days_by_day = {day["day"]: day for day in response.context["availability"]["days"]}
    assert response.status_code == 200
    assert days_by_day[10]["label"] == "Livre"
    assert days_by_day[10]["reservations"] == []
    assert b"Churrasqueira" not in response.content


@pytest.mark.django_db
def test_reservation_availability_selector_blocks_cross_tenant_amenity(
    reservations_context,
):
    with pytest.raises(Http404):
        list_reservation_days_for_amenity(
            condominium=reservations_context["condo_a"],
            amenity=reservations_context["amenity_b"],
            month_date=timezone.localdate(),
        )


@pytest.mark.django_db
def test_resident_cannot_request_with_other_condominium_amenity(client, reservations_context):
    start_at, end_at = future_window()
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_b"].id),
            "start_at": datetime_input(start_at),
            "end_at": datetime_input(end_at),
            "notes": "Nao deve salvar",
        },
    )

    assert response.status_code == 200
    assert not Reservation.objects.filter(
        condominium=reservations_context["condo_a"],
        notes="Nao deve salvar",
    ).exists()


@pytest.mark.django_db
def test_resident_cannot_request_past_reservation(client, reservations_context):
    start_at = timezone.now() - timedelta(hours=2)
    end_at = timezone.now() + timedelta(hours=1)
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "start_at": datetime_input(start_at),
            "end_at": datetime_input(end_at),
            "notes": "Data passada",
        },
    )

    assert response.status_code == 200
    assert not Reservation.objects.filter(notes="Data passada").exists()


@pytest.mark.django_db
def test_resident_cannot_request_reservation_with_inactive_amenity(
    client,
    reservations_context,
):
    start_at, end_at = future_window()
    reservations_context["amenity_a"].soft_delete(user=reservations_context["syndic"])
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "start_at": datetime_input(start_at),
            "end_at": datetime_input(end_at),
            "notes": "Area inativa",
        },
    )

    assert response.status_code == 200
    assert not Reservation.objects.filter(notes="Area inativa").exists()


@pytest.mark.django_db
def test_resident_cannot_request_reservation_with_invalid_time_range(
    client,
    reservations_context,
):
    start_at, _ = future_window()
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_create"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "start_at": datetime_input(start_at),
            "end_at": datetime_input(start_at),
            "notes": "Horario invalido",
        },
    )

    assert response.status_code == 200
    assert not Reservation.objects.filter(notes="Horario invalido").exists()


@pytest.mark.django_db
def test_resident_sees_only_own_reservations_from_active_condominium(
    client,
    reservations_context,
):
    own_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
    )
    make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:reservation_list"))

    assert response.status_code == 200
    assert str(own_reservation.amenity.name).encode() in response.content
    assert b"Churrasqueira" not in response.content
    assert response.content.count(b"Salao de festas") == 2


@pytest.mark.django_db
def test_resident_cannot_view_other_residents_reservation(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:reservation_detail", args=[reservation.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_resident_cannot_access_other_condominium_reservation(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:reservation_detail", args=[reservation.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_manager_sees_reservations_from_active_condominium(client, reservations_context):
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(reverse("reservations:admin_reservation_list"))

    assert response.status_code == 200
    assert b"Salao de festas" in response.content
    assert b"Churrasqueira" not in response.content


@pytest.mark.django_db
def test_admin_reservation_list_filters_by_status(client, reservations_context):
    pending_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.PENDING,
    )
    approved_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        status=ReservationStatus.APPROVED,
        days=2,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:admin_reservation_list"),
        {"status": ReservationStatus.PENDING},
    )

    assert response.status_code == 200
    assert list(response.context["reservations"]) == [pending_reservation]
    assert approved_reservation not in response.context["reservations"]


@pytest.mark.django_db
def test_admin_reservation_list_filters_by_amenity(client, reservations_context):
    second_amenity = Amenity.objects.create(
        condominium=reservations_context["condo_a"],
        name="Piscina",
    )
    target_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    other_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=second_amenity,
        requested_by=reservations_context["second_resident"],
        days=2,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:admin_reservation_list"),
        {"amenity": str(reservations_context["amenity_a"].id)},
    )

    assert response.status_code == 200
    assert list(response.context["reservations"]) == [target_reservation]
    assert other_reservation not in response.context["reservations"]


@pytest.mark.django_db
def test_admin_reservation_list_combines_filters(client, reservations_context):
    second_amenity = Amenity.objects.create(
        condominium=reservations_context["condo_a"],
        name="Piscina",
    )
    target_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        status=ReservationStatus.PENDING,
        days=2,
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=second_amenity,
        requested_by=reservations_context["second_resident"],
        status=ReservationStatus.APPROVED,
        days=3,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:admin_reservation_list"),
        {
            "amenity": str(reservations_context["amenity_a"].id),
            "status": ReservationStatus.APPROVED,
        },
    )

    assert response.status_code == 200
    assert list(response.context["reservations"]) == [target_reservation]


@pytest.mark.django_db
def test_admin_reservation_filter_rejects_other_condominium_amenity_safely(
    client,
    reservations_context,
):
    reservation_a = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    reservation_b = make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.get(
        reverse("reservations:admin_reservation_list"),
        {"amenity": str(reservations_context["amenity_b"].id)},
    )

    assert response.status_code == 200
    assert reservation_a in response.context["reservations"]
    assert reservation_b not in response.context["reservations"]
    assert b"Churrasqueira" not in response.content


@pytest.mark.django_db
def test_manager_approves_reservation_with_audit_log(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_approve", args=[reservation.id]),
        {"manager_notes": "Aprovado"},
    )

    assert response.status_code == 302
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.APPROVED
    assert reservation.decided_by == reservations_context["syndic"]
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.reservation.approved",
        object_id=str(reservation.id),
        changes={"status": {"from": ReservationStatus.PENDING, "to": ReservationStatus.APPROVED}},
    ).exists()


@pytest.mark.django_db
def test_manager_cannot_approve_overlapping_reservation(client, reservations_context):
    existing = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    pending = Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        start_at=existing.start_at + timedelta(minutes=30),
        end_at=existing.end_at + timedelta(minutes=30),
        status=ReservationStatus.PENDING,
        created_by=reservations_context["second_resident"],
        updated_by=reservations_context["second_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(reverse("reservations:reservation_approve", args=[pending.id]))

    assert response.status_code == 302
    pending.refresh_from_db()
    assert pending.status == ReservationStatus.PENDING
    assert not AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        action="reservations.reservation.approved",
        object_id=str(pending.id),
    ).exists()


@pytest.mark.django_db
def test_cancelled_and_rejected_reservations_do_not_block_approval(
    client,
    reservations_context,
):
    rejected = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.REJECTED,
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        status=ReservationStatus.CANCELLED,
    )
    pending = Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        start_at=rejected.start_at + timedelta(minutes=30),
        end_at=rejected.end_at - timedelta(minutes=30),
        status=ReservationStatus.PENDING,
        created_by=reservations_context["second_resident"],
        updated_by=reservations_context["second_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(reverse("reservations:reservation_approve", args=[pending.id]))

    assert response.status_code == 302
    pending.refresh_from_db()
    assert pending.status == ReservationStatus.APPROVED


@pytest.mark.django_db
def test_pending_reservation_does_not_block_approval(client, reservations_context):
    existing_pending = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.PENDING,
    )
    pending = Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        start_at=existing_pending.start_at + timedelta(minutes=30),
        end_at=existing_pending.end_at - timedelta(minutes=30),
        status=ReservationStatus.PENDING,
        created_by=reservations_context["second_resident"],
        updated_by=reservations_context["second_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(reverse("reservations:reservation_approve", args=[pending.id]))

    assert response.status_code == 302
    pending.refresh_from_db()
    assert pending.status == ReservationStatus.APPROVED


@pytest.mark.django_db
def test_adjacent_approved_reservation_does_not_block_approval(client, reservations_context):
    existing = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    pending = Reservation.objects.create(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
        start_at=existing.end_at,
        end_at=existing.end_at + timedelta(hours=2),
        status=ReservationStatus.PENDING,
        created_by=reservations_context["second_resident"],
        updated_by=reservations_context["second_resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(reverse("reservations:reservation_approve", args=[pending.id]))

    assert response.status_code == 302
    pending.refresh_from_db()
    assert pending.status == ReservationStatus.APPROVED


@pytest.mark.django_db
def test_rejected_or_cancelled_reservation_cannot_be_approved(client, reservations_context):
    rejected = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.REJECTED,
    )
    cancelled = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.CANCELLED,
        days=2,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    rejected_response = client.post(reverse("reservations:reservation_approve", args=[rejected.id]))
    cancelled_response = client.post(reverse("reservations:reservation_approve", args=[cancelled.id]))

    assert rejected_response.status_code == 302
    assert cancelled_response.status_code == 302
    rejected.refresh_from_db()
    cancelled.refresh_from_db()
    assert rejected.status == ReservationStatus.REJECTED
    assert cancelled.status == ReservationStatus.CANCELLED


@pytest.mark.django_db
def test_manager_rejects_reservation_with_audit_log(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_reject", args=[reservation.id]),
        {"manager_notes": "Indisponivel"},
    )

    assert response.status_code == 302
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.REJECTED
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.reservation.rejected",
        object_id=str(reservation.id),
        changes={"status": {"from": ReservationStatus.PENDING, "to": ReservationStatus.REJECTED}},
    ).exists()


@pytest.mark.django_db
def test_manager_cancels_reservation_with_audit_log(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    response = client.post(
        reverse("reservations:reservation_cancel", args=[reservation.id]),
        {"manager_notes": "Manutencao emergencial"},
    )

    assert response.status_code == 302
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.CANCELLED
    assert reservation.cancelled_by == reservations_context["syndic"]
    assert AuditLog.objects.filter(
        condominium=reservations_context["condo_a"],
        actor=reservations_context["syndic"],
        action="reservations.reservation.cancelled",
        object_id=str(reservation.id),
        changes={"status": {"from": ReservationStatus.APPROVED, "to": ReservationStatus.CANCELLED}},
    ).exists()


@pytest.mark.django_db
def test_resident_cannot_approve_or_cancel_reservation(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    client.login(username="resident", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    approve_response = client.post(reverse("reservations:reservation_approve", args=[reservation.id]))
    reject_response = client.post(reverse("reservations:reservation_reject", args=[reservation.id]))
    cancel_response = client.post(reverse("reservations:reservation_cancel", args=[reservation.id]))

    assert approve_response.status_code == 403
    assert reject_response.status_code == 403
    assert cancel_response.status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.PENDING


@pytest.mark.django_db
def test_reservation_actions_reject_get(client, reservations_context):
    reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    client.login(username="syndic", password="testpass123")
    activate_condominium(client, reservations_context["condo_a"])

    approve_response = client.get(reverse("reservations:reservation_approve", args=[reservation.id]))
    reject_response = client.get(reverse("reservations:reservation_reject", args=[reservation.id]))
    cancel_response = client.get(reverse("reservations:reservation_cancel", args=[reservation.id]))

    assert approve_response.status_code == 405
    assert reject_response.status_code == 405
    assert cancel_response.status_code == 405
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.PENDING


@pytest.mark.django_db
def test_reservation_services_block_cross_tenant_actions(reservations_context):
    reservation_b = make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )

    with pytest.raises(ValidationError):
        request_reservation(
            condominium=reservations_context["condo_a"],
            actor=reservations_context["resident"],
            amenity=reservations_context["amenity_b"],
            start_at=future_window()[0],
            end_at=future_window()[1],
        )

    reservations_context["amenity_a"].soft_delete(user=reservations_context["syndic"])
    start_at, end_at = future_window()
    with pytest.raises(ValidationError):
        request_reservation(
            condominium=reservations_context["condo_a"],
            actor=reservations_context["resident"],
            amenity=reservations_context["amenity_a"],
            start_at=start_at,
            end_at=end_at,
        )

    with pytest.raises(ValidationError):
        update_amenity(
            condominium=reservations_context["condo_a"],
            actor=reservations_context["syndic"],
            amenity=reservations_context["amenity_b"],
            name="Area cruzada",
        )

    with pytest.raises(ValidationError):
        approve_reservation(
            condominium=reservations_context["condo_a"],
            actor=reservations_context["syndic"],
            reservation=reservation_b,
        )

    with pytest.raises(ValidationError):
        cancel_reservation(
            condominium=reservations_context["condo_a"],
            actor=reservations_context["syndic"],
            reservation=reservation_b,
        )


@pytest.mark.django_db
def test_reservation_selectors_filter_by_condominium_and_user(reservations_context):
    own_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
    )
    other_user_reservation = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["second_resident"],
    )
    make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
    )

    manager_reservations = list(
        list_reservations_for_manager(condominium=reservations_context["condo_a"]),
    )
    resident_reservations = list(
        list_reservations_for_user(
            condominium=reservations_context["condo_a"],
            user=reservations_context["resident"],
        ),
    )

    assert set(manager_reservations) == {own_reservation, other_user_reservation}
    assert resident_reservations == [own_reservation]


@pytest.mark.django_db
def test_dashboard_reservation_indicators_do_not_break_without_reservations(
    reservations_context,
):
    summary = get_syndic_dashboard_summary(condominium=reservations_context["condo_a"])

    assert summary["pending_reservations"] == 0
    assert summary["approved_reservations_this_month"] == 0


@pytest.mark.django_db
def test_dashboard_counts_reservations_for_active_condominium_only(reservations_context):
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.PENDING,
    )
    make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    inactive = make_reservation(
        condominium=reservations_context["condo_a"],
        amenity=reservations_context["amenity_a"],
        requested_by=reservations_context["resident"],
        status=ReservationStatus.APPROVED,
    )
    inactive.soft_delete(user=reservations_context["syndic"])
    make_reservation(
        condominium=reservations_context["condo_b"],
        amenity=reservations_context["amenity_b"],
        requested_by=reservations_context["other_resident"],
        status=ReservationStatus.PENDING,
    )

    summary = get_syndic_dashboard_summary(condominium=reservations_context["condo_a"])

    assert summary["pending_reservations"] == 1
    assert summary["approved_reservations_this_month"] == 1
