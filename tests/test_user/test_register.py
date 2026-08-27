import pytest
from user.models import CentralUser, TwoFactory
from user_profile.models import UserProfile


@pytest.mark.django_db
def test_register_user_without_last_name_and_phone_number(client):
    payload = {
        "email": "jan_kowalski@example.com",
        "first_name": "Jan",
        "password": "strongPassword123!",
    }

    response = client.post("/api/v1/user/register/", payload, format="json")
    assert response.status_code == 201
    assert "challenge_id" in response.data

    user = CentralUser.objects.get(email="jan_kowalski@example.com")
    assert user is not None
    assert user.is_user_activated is False

    profile = UserProfile.objects.get(user=user)
    assert profile.name == "Jan"
    assert profile.surname is None
    assert profile.phone_number is None


@pytest.mark.django_db
def test_register_user_with_optional_fields(client):
    payload = {
        "email": "adam_nowak@example.com",
        "first_name": "Adam",
        "last_name": "Nowak",
        "phone_number": "+48123456789",
        "password": "strongPassword123!",
    }

    response = client.post("/api/v1/user/register/", payload, format="json")
    assert response.status_code == 201

    user = CentralUser.objects.get(email="adam_nowak@example.com")
    profile = UserProfile.objects.get(user=user)
    assert profile.name == "Adam"
    assert profile.surname == "Nowak"
    assert profile.phone_number == "+48123456789"
