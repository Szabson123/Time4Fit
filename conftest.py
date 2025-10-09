import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='123')

@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user)
    return api_client, user