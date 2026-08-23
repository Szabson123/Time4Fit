import os
import re
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from django.template.loader import render_to_string
from django.conf import settings
from PIL import Image, ImageDraw
import time

@shared_task
def send_welcome_email(to_email, message_or_code, purpose="login"):
    """
    Wysyła kod weryfikacyjny (OTP) w postaci estetycznej wiadomości HTML z logo Time4Fit.
    Obsługuje cele: register, login, reset_password.
    """
    code = message_or_code
    
    # Jeśli przekazano pełny tekst (np. wywołanie w starym formacie), wyciągamy kod i cel
    if isinstance(message_or_code, str) and len(message_or_code) > 10:
        match = re.search(r'\b\d{6}\b', message_or_code)
        if match:
            code = match.group(0)
        
        msg_lower = message_or_code.lower()
        if "rejestracj" in msg_lower:
            purpose = "register"
        elif "hasł" in msg_lower:
            purpose = "reset_password"
        elif "logowani" in msg_lower:
            purpose = "login"

    if purpose == "register":
        subject = "Witaj w Time4Fit! Kod rejestracyjny"
        title = "Weryfikacja konta"
        heading = "Potwierdź swój adres e-mail"
        body_text = "Dziękujemy za dołączenie do Time4Fit! Użyj poniższego kodu, aby dokończyć rejestrację konta."
    elif purpose == "reset_password":
        subject = "Time4Fit - Resetowanie hasła"
        title = "Reset hasła"
        heading = "Prośba o zmianę hasła"
        body_text = "Otrzymaliśmy prośbę o zmianę hasła do Twojego konta Time4Fit. Użyj poniższego kodu weryfikacyjnego."
    else:  # "login" lub domyślnie
        subject = "Time4Fit - Kod weryfikacyjny do logowania"
        title = "Kod logowania"
        heading = "Witaj ponownie w Time4Fit!"
        body_text = "Wpisz poniższy kod, aby bezpiecznie zalogować się do aplikacji."

    context = {
        'title': title,
        'heading': heading,
        'body_text': body_text,
        'code': code,
        'purpose': purpose,
    }

    html_content = render_to_string('user/email_otp.html', context)
    text_content = f"{heading}\n\n{body_text}\n\nTwój kod: {code}\n\nKod jest ważny przez 5 minut."

    from_email = settings.EMAIL_HOST_USER
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")

    # Ścieżka do logo umieszczonego w static
    logo_path = settings.BASE_DIR / 'user' / 'static' / 'user' / 'images' / 'logo.png'
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            mime_image = MIMEImage(f.read())
            mime_image.add_header('Content-ID', '<logo_img>')
            mime_image.add_header('Content-Disposition', 'inline', filename='logo.png')
            msg.attach(mime_image)

    msg.send()
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