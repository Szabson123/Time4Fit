import pytest
from django.core import mail
from user.tasks import send_welcome_email

@pytest.mark.django_db
def test_send_welcome_email_html_and_logo_attachment():
    # Run task directly (synchronously)
    send_welcome_email("testuser@example.com", "123456", purpose="register")

    # Check outbox
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]

    assert sent_email.to == ["testuser@example.com"]
    assert "Witaj w Time4Fit!" in sent_email.subject
    
    # Check text & html alternatives
    assert "123456" in sent_email.body
    
    # Verify HTML alternative exists
    html_alternatives = [content for content, mimetype in sent_email.alternatives if mimetype == "text/html"]
    assert len(html_alternatives) == 1
    html_body = html_alternatives[0]
    
    # Verify CID logo reference in HTML
    assert 'src="cid:logo_img"' in html_body
    assert '123456' in html_body
    assert 'Potwierdź swój adres e-mail' in html_body

    # Verify attachment contains logo MIMEImage
    assert len(sent_email.attachments) == 1
    attachment = sent_email.attachments[0]
    assert attachment.get_filename() == 'logo.png'
    assert attachment.get('Content-ID') == '<logo_img>'


@pytest.mark.django_db
def test_send_welcome_email_login_purpose():
    mail.outbox.clear()
    send_welcome_email("loginuser@example.com", "654321", purpose="login")

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert "Kod weryfikacyjny do logowania" in sent_email.subject

    html_alternatives = [content for content, mimetype in sent_email.alternatives if mimetype == "text/html"]
    assert "654321" in html_alternatives[0]
    assert "Witaj ponownie w Time4Fit!" in html_alternatives[0]


@pytest.mark.django_db
def test_send_welcome_email_reset_password_purpose():
    mail.outbox.clear()
    send_welcome_email("resetuser@example.com", "999888", purpose="reset_password")

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert "Resetowanie hasła" in sent_email.subject

    html_alternatives = [content for content, mimetype in sent_email.alternatives if mimetype == "text/html"]
    assert "999888" in html_alternatives[0]
    assert "Prośba o zmianę hasła" in html_alternatives[0]


@pytest.mark.django_db
def test_reset_password_view_sends_email(client):
    from user.models import CentralUser
    mail.outbox.clear()

    # Create user
    user = CentralUser.objects.create_user(email="UserReset@example.com", password="password123")
    user.is_user_activated = True
    user.save()

    # Call reset password API (with lowercase email test)
    response = client.post("/user/reset_password/", {"email": "userreset@example.com"}, format="json")
    assert response.status_code == 200

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == ["UserReset@example.com"]
    assert "Resetowanie hasła" in sent_email.subject
    
    html_alternatives = [content for content, mimetype in sent_email.alternatives if mimetype == "text/html"]
    assert len(html_alternatives) == 1
    assert "Prośba o zmianę hasła" in html_alternatives[0]

