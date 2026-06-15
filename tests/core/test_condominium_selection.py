import pytest
from django.urls import reverse

from apps.core.middleware import ACTIVE_CONDOMINIUM_SESSION_KEY
from apps.core.models import Condominium, CondominiumMembership, CondominiumRole


@pytest.mark.django_db
def test_select_condominium_view_blocks_unlinked_condominium(client, user_factory):
    user = user_factory(username="resident", password="testpass123")
    condo_a = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    condo_b = Condominium.objects.create(name="Condominio B", slug="condominio-b")
    CondominiumMembership.objects.create(
        condominium=condo_a,
        user=user,
        role=CondominiumRole.RESIDENT,
    )
    client.login(username="resident", password="testpass123")

    response = client.post(
        reverse("core:condominium_select"),
        {"condominium_id": str(condo_b.id)},
    )

    assert response.status_code == 200
    assert ACTIVE_CONDOMINIUM_SESSION_KEY not in client.session


@pytest.mark.django_db
def test_select_condominium_view_sets_active_condominium(client, user_factory):
    user = user_factory(username="resident", password="testpass123")
    condo = Condominium.objects.create(name="Condominio A", slug="condominio-a")
    CondominiumMembership.objects.create(
        condominium=condo,
        user=user,
        role=CondominiumRole.RESIDENT,
    )
    client.login(username="resident", password="testpass123")

    response = client.post(
        reverse("core:condominium_select"),
        {"condominium_id": str(condo.id)},
    )

    assert response.status_code == 302
    assert client.session[ACTIVE_CONDOMINIUM_SESSION_KEY] == str(condo.id)
