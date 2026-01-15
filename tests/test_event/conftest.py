from django.utils import timezone
from datetime import timedelta
import pytest
from .factories import EventFactory, UserFactory, EventInvitationFactory
from pytest_factoryboy import register

@pytest.fixture
def event_payload_factory():
    def factory(**overrides):
        payload = {
            "title": "string",
            "short_desc": "string",
            "long_desc": "string",
            "date_time_event": timezone.now() + timedelta(minutes=30),
            "duration_min": 2147483647,
            "latitude": 90,
            "longitude": 180,
            "public_event": True,
            "country": "string",
            "city": "string",
            "street": "string",
            "street_number": "string",
            "flat_number": "string",
            "zip_code": "string",
            "additional_info": {
                "advanced_level": "none",
                "places_for_people_limit": 2147483647,
                "age_limit": "string",
                "price": "91452.",
                "payment_in_app": True,
                "special_guests": [
                {
                    "name": "string",
                    "surname": "string",
                    "nickname": "string"
                }
                ]
            }
        }
        
        payload.update(overrides)
        return payload
    return factory


register(EventFactory)
register(UserFactory)
register(EventInvitationFactory)