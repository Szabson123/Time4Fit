from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from PIL import Image, ImageDraw
import time

@shared_task
def send_welcome_email(to_email, message):
    subject = 'Witaj!'
    from_email = settings.EMAIL_HOST_USER
    
    send_mail(subject, message, from_email, [to_email])
    return f'Mail wysłany do {to_email}'


@shared_task(name="core.tasks.async_generate_report_task")
def async_generate_report_task(user_id):
    """
    Zadanie Celery dedykowane do asynchronicznego przetwarzania w tle.
    Całkowicie odizolowane od cyklu żądanie-odpowiedź serwera HTTP.
    """
    # 1. Sekcja CPU-bound: Intensywne renderowanie grafiki raportu przy użyciu Pillow
    # Dokładnie taki sam algorytm obciążający rdzeń procesora jak w modelu synchronicznym
    image = Image.new("RGB", (1500, 1500), color="white")
    draw = ImageDraw.Draw(image)
    for i in range(7500):
        draw.text((10, 10), f"Raport ID: {user_id} - Iteracja: {i}", fill="black")
        
    # 2. Sekcja I/O-bound: Symulacja zapisu dyskowego lub zewnętrznego API
    # Zgodnie z metodologią badawczą opóźnienie wynosi 400 ms
    time.sleep(0.4)
    
    # Zwracany status logowany jest w metrykach Celery (np. Flower lub bazie danych)
    return f"Raport dla użytkownika o ID {user_id} został pomyślnie wygenerowany."