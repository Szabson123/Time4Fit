import uuid

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from decimal import Decimal

from user.models import CentralUser


ADVANCED_LEVEL = [
    ('none', 'None'),
    ('beginner', 'Beginner'),
    ('semi-advanced', 'Semi-advanced'),
    ('advanced', 'Advanced'),
    ('all', 'All'),
]

PARTICIPANT_ROLES = [
    ('participant', 'Participant'),
    ('admin', 'Admin'),
    ('trainer', 'Trainer'),
]

class Category(models.Model):
    name = models.CharField(max_length=255)


class Event(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    author = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    short_desc = models.CharField(max_length=255)
    long_desc = models.TextField(null=True, blank=True)
    date_time_event = models.DateTimeField()
    duration_min = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    # For map
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])

    # For user
    country = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    street_number = models.CharField(max_length=255, blank=True, null=True)
    flat_number = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=255, blank=True, null=True)
    public_event = models.BooleanField(default=True)


class EventAdditionalInfo(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="additional_info")
    advanced_level = models.CharField(choices=ADVANCED_LEVEL, max_length=255, default='none')
    places_for_people_limit = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    age_limit = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.00'))], default="0.00")
    payment_in_app = models.BooleanField(default=False)


class SpecialGuests(models.Model):
    add_info = models.ForeignKey(EventAdditionalInfo, on_delete=models.CASCADE, related_name='special_guests')
    name = models.CharField(max_length=255, null=True, blank=True)
    surname = models.CharField(max_length=255, null=True, blank=True)
    nickname = models.CharField(max_length=255, null=True, blank=True)


class EventParticipant(models.Model):
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, related_name='eventparticipant')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='eventparticipant')

    role = models.CharField(max_length=255, choices=PARTICIPANT_ROLES, default='participant')
    paid_status = models.BooleanField(default=False)
    presence = models.BooleanField(null=True, default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event')
        ]

    def __str__(self):
        return f"{self.user} in {self.event} ({self.role})"


class EventInvitation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='eventinvitation')
    code = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    is_one_use = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    created_by = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    
    @property
    def link(self):
        return f"{settings.FRONT_LINK}{self.code}"
    
    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_used and self.event.date_time_event >= timezone.now()