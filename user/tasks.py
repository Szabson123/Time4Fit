from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_welcome_email(to_email, message):
    subject = 'Witaj!'
    from_email = settings.EMAIL_HOST_USER
    
    send_mail(subject, message, from_email, [to_email])
    return f'Mail wysłany do {to_email}'