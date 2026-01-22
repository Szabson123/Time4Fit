from django.db import models
from django.utils import timezone
from user.models import CentralUser

class Plan(models.Model):
    name = models.CharField(max_length=255)
    stripe_price_id = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    interval = models.CharField(choices=[('month', 'Miesięczny'), ('year', 'Roczny')], max_length=10)


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Aktywna'),
        ('past_due', 'Zaległa płatność'),
        ('canceled', 'Anulowana'),
        ('trialing', 'Okres próbny'),
    ]

    user = models.OneToOneField(CentralUser, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    
    stripe_subscription_id = models.CharField(max_length=100, blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    
    current_period_end = models.DateTimeField(null=True, blank=True)

    @property
    def is_valid(self):
        """Sprawdza czy subskrypcja jest aktywna i opłacona."""
        if self.status == 'active':
            return self.current_period_end > timezone.now()
        if self.status == 'canceled' and self.current_period_end:
            return self.current_period_end > timezone.now()
        return False