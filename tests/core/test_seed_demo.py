from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command

from apps.accounts.models import User
from apps.communication.models import Announcement, AnnouncementStatus
from apps.core.models import Condominium, CondominiumMembership, Unit, UnitOccupancy
from apps.documents.models import Document
from apps.reservations.models import Reservation, ReservationStatus
from apps.tickets.models import Ticket


@pytest.mark.django_db
def test_seed_demo_condominium_creates_idempotent_demo_data(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    first_output = StringIO()
    second_output = StringIO()
    call_command("seed_demo_condominium", stdout=first_output)
    call_command("seed_demo_condominium", stdout=second_output)

    condominium = Condominium.active_objects.get(slug="condominio-demo")
    syndic = User.objects.get(email="sindico.demo@example.com")
    resident = User.objects.get(email="morador.demo@example.com")

    assert Condominium.active_objects.filter(slug="condominio-demo").count() == 1
    assert CondominiumMembership.active_objects.filter(condominium=condominium).count() == 2
    assert Unit.active_objects.filter(condominium=condominium, number="101").count() == 1
    assert UnitOccupancy.active_objects.filter(
        condominium=condominium,
        user=resident,
    ).count() == 1
    assert Announcement.active_objects.filter(
        condominium=condominium,
        status=AnnouncementStatus.PUBLISHED,
    ).count() == 1
    assert Ticket.active_objects.filter(condominium=condominium, created_by=resident).count() == 1
    assert Document.active_objects.filter(condominium=condominium, created_by=syndic).count() == 1
    assert Reservation.active_objects.filter(
        condominium=condominium,
        requested_by=resident,
        status=ReservationStatus.APPROVED,
    ).count() == 1
    assert authenticate(username="sindico_demo", password="Demo@12345") == syndic
    assert authenticate(username="morador_demo", password="Demo@12345") == resident
    assert "Seed demo concluida." in first_output.getvalue()
    assert "Seed demo concluida." in second_output.getvalue()
