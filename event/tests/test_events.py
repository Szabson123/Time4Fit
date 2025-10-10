import pytest
from rest_framework import status
from django.utils import timezone
from event.models import Event

@pytest.mark.django_db
def test_event_create(auth_client):
    client, user = auth_client

    url = "/event/events/"
    payload = {
        "title": "Testowy event",
        "short_desc": "string",
        "long_desc": "string",
        "date_time_event": "2025-10-10T13:15:59.006Z",
        "duration_min": 5,
        "latitude": 0,
        "longitude": 0,
        "public_event": True,
        "country": "string",
        "city": "string",
        "street": "string",
        "street_number": "string",
        "flat_number": "string",
        "zip_code": "string",
        "additional_info": {
            "advanced_level": "none",
            "places_for_people_limit": 10,
            "age_limit": "string",
            "participant_list_show": True,
            "price": "0.00",
            "payment_in_app": True,
            "special_guests": [
            {
                "name": "string",
                "surname": "string"
            }
            ]
        }
    }

    response = client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED

    event = Event.objects.first()
    assert event is not None
    assert event.title == "Testowy event"
    assert event.author == user