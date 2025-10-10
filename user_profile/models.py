from django.db import models
from user.models import CentralUser


Sex_choices = [
    ('male', 'Male'),
    ('female', 'Famale'),
    ('none', 'None'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(CentralUser, on_delete=models.CASCADE, related_name="profile")

    name = models.CharField(max_length=255, null=True, blank=True)
    surname = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    
    profile_description = models.TextField(null=True, blank=True)
    show_profile_public = models.BooleanField(default=False)

    birth_day = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=255, choices=Sex_choices, default='none')
    profile_picture = models.ImageField(null=True, blank=True, upload_to="profile_pictures/")
