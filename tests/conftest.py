import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

CentralUser = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def central_user(db):
    return CentralUser.objects.create_user(
        email="test@test.com",
        password="password123",
        is_active=True,
        is_user_activated=True,
    )


@pytest.fixture
def jwt_token(central_user):
    refresh = RefreshToken.for_user(central_user)
    return str(refresh.access_token)


@pytest.fixture
def auth_api_client(api_client, jwt_token):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}"
    )
    return api_client