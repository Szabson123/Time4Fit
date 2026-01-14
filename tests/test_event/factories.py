import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import timedelta
import pytest
from event.models import Event
from user.models import CentralUser
from user_profile.models import UserProfile


class UserFactory(DjangoModelFactory):
    class Meta:
        model = CentralUser
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall(
        "set_password", "TestPassword123"
    )

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        if not create:
            return
        UserProfile.objects.create(
            user=self,
            name="Factory",
            surname="User",
        )


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event
    
    title = "string"
    short_desc = "string"
    long_desc = "string"
    date_time_event = timezone.now() + timedelta(minutes=30)
    duration_min = 50
    latitude = 90
    longitude = 180
    public_event = True
    country = "Polska"
    city = "Sosnowiec"
    street = "Jagiello"
    street_number = "50"
    flat_number = "10"
    zip_code = "41-215"