import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user_factory(db):
    counter = {"value": 0}
    User = get_user_model()

    def make_user(**kwargs):
        counter["value"] += 1
        index = counter["value"]
        username = kwargs.pop("username", f"user{index}")
        email = kwargs.pop("email", f"user{index}@example.com")
        password = kwargs.pop("password", "testpass123")
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **kwargs,
        )

    return make_user
