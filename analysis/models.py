from django.db import models


class ApplicationUser(models.Model):
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=255)
    is_valid = models.BooleanField(default=False)