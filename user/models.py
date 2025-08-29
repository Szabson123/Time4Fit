from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
import uuid

from django.utils import timezone
import hmac
from .utils import hmac_code, default_expires


class CentralUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CentralUser(AbstractBaseUser):
    # Basic Login
    email = models.EmailField(unique=True)

    # Only for django-admin
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    is_user_activated = models.BooleanField(default=False)

    # Additional
    first_name = models.CharField(max_length=127)
    last_name = models.CharField(max_length=127)
    phone_number = models.CharField(max_length=20)

    objects = CentralUserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser
    

class TwoFactory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=255, default="register") 
    code_hmac = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    attempts = models.IntegerField(default=0)
    attempts_limit = models.IntegerField(default=5)

    @property
    def is_expired(self): return timezone.now() >= self.expires_at
    @property
    def is_used(self): return self.used_at is not None

    def verify(self, code_input: str):
        if self.is_used or self.is_expired or self.attempts >= self.attempts_limit:
            return False
        
        self.attempts += 1
        ok = hmac.compare_digest(hmac_code(code_input), self.code_hmac)
        
        self.save(update_fields=["attempts"])
        if ok:
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])

        return ok

