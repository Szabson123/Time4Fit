import pytest
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db()
def test_fail_event_unauthorized(api_client, event_payload_factory):
    url = f'/event/events/'
    payload = event_payload_factory()
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 401, f"Otrzymano błąd walidacji: {response.data}"
    assert 'Authentication credentials were not provided' in str(response.data)

@pytest.mark.django_db
def test_happy_path_create_event(auth_api_client, event_payload_factory):
    url = f'/event/events/'
    payload = event_payload_factory()
    response = auth_api_client.post(url, payload, format='json')
    assert response.status_code == 201, f"Otrzymano błąd walidacji {response.data}"