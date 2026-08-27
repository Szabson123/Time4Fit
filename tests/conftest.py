import pytest
from rest_framework.test import APIClient
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def extend_postgres(sender, connection, **kwargs):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


from pytest_factoryboy import register
from tests.test_event.factories import UserFactory

register(UserFactory)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_api_client(api_client, user_factory):
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client, user

@pytest.fixture(autouse=True)
def use_fast_password_hasher(settings):
    """Wymusza użycie szybkiego haszowania haseł w testach."""
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]