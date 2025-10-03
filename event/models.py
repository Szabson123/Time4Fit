from django.db import models
import uuid
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from user.models import CentralUser
from datetime import timezone
import os
from django.conf import settings

Advanced_Level = (
    ('none', 'None'),
    ('begginer', 'Begginer'),
    ('semi-advanced', 'Semi-advanced'),
    ('advanced', 'Advanced'),
    ('all', 'All')
)

Age_Groups = (
    ('<12', '<12'),
    ('12 - 16', '12 - 16'),
    # Add more
)   

Roles_Participant = (
    ('participant', 'Participant'),
    ('admin', 'Admin'),
    ('treiner', 'Trainer')
)

class Category(models.Model):
    name = models.CharField(max_length=255)


class Event(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4)
    author = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    short_desc = models.CharField(max_length=255)
    long_desc = models.TextField(null=True, blank=True)
    date_time_event = models.DateTimeField()
    duration_min = models.PositiveIntegerField()

    # For map
    latitude = models.FloatField()
    longitude = models.FloatField()

    # For user
    country = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    street_number = models.CharField(max_length=255)
    flat_number = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)


class EventAdditionalInfo(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="additional_info")
    advanced_level = models.CharField(choices=Advanced_Level, max_length=255, default='none')
    places_for_people_limit = models.PositiveIntegerField()
    age_limit = models.CharField(choices=Age_Groups, max_length=255)
    participant_list_show = models.BooleanField(default=False)
    public_event = models.BooleanField(default=True)
    free = models.BooleanField(default=False)
    price = models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(0.0)], default="0.00")
    payment_in_app = models.BooleanField(default=False)

    def full_clean(self):
        if self.free and self.price != "0.00":
            raise ValidationError("If free cant put price")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SpecialGuests(models.Model):
    add_info = models.ForeignKey(EventAdditionalInfo, on_delete=models.CASCADE, related_name='special_guests')
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)


class EventParticipant(models.Model):
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, related_name='eventparticipant')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='eventparticipant')

    role = models.CharField(max_length=255, choices=Roles_Participant, default='participant')
    paid_status = models.BooleanField(default=False)
    presense = models.BooleanField(null=True, default=True)


class EventInvitation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='eventinvitation')
    code = models.CharField(max_length=8)
    date_added = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    is_one_use = models.BooleanField(default=False)
    
    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.event.date_time_event
    
    @property
    def link(self):
        return f"{settings.FRONT_LINK}{self.code}"
    