import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Time4Fit.settings')

app = Celery('Time4Fit')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()