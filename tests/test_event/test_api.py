import pytest
from django.utils import timezone
from datetime import timedelta
from event.models import Event, EventInvitation
from .factories import EventFactory
import threading
from django.db import connections


@pytest.mark.django_db()
def test_fail_event_unauthorized(api_client, event_payload_factory):
    url = f'/event/events/'
    payload = event_payload_factory()
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 401, f"Otrzymano błąd walidacji: {response.data}"
    assert 'Authentication credentials were not provided' in str(response.data)

@pytest.mark.django_db
def test_happy_path_create_event(auth_api_client, event_payload_factory):
    client, user = auth_api_client

    url = f'/event/events/'
    payload = event_payload_factory()
    response = client.post(url, payload, format='json')

    assert response.status_code == 201, f"Otrzymano błąd walidacji {response.data}"
    ev = Event.objects.get()
    assert ev.date_time_event == payload["date_time_event"]

@pytest.mark.django_db
def test_public_private_event_list(api_client, event_factory, user_factory):
    user = user_factory()

    public_event1 = event_factory(author=user)
    public_event2 = event_factory(author=user)
    private_event = event_factory(public_event=False, author=user)

    url = f'/event/events/'

    response = api_client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 2

@pytest.mark.django_db
def test_public_private_event_list_but_author(auth_api_client, event_factory, user_factory):
    client, user = auth_api_client

    public_event1 = event_factory(author=user)
    public_event2 = event_factory(author=user)
    private_event = event_factory(public_event=False, author=user)

    url = f'/event/events/'

    response = client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 3

@pytest.mark.django_db
def test_annon_dont_see_events_in_past(api_client, event_factory, user_factory):
    user = user_factory()

    public_event1 = event_factory(author=user)
    public_event2 = event_factory(author=user, date_time_event=timezone.now() - timedelta(minutes=10))
    private_event = event_factory(public_event=False, author=user)

    url = f'/event/events/'

    response = api_client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1

@pytest.mark.django_db
def test_annon_dont_see_events_in_past_even_if_knows_title(api_client, event_factory, user_factory):
    user = user_factory()

    public_event1 = event_factory(author=user)
    public_event2 = event_factory(author=user, date_time_event=timezone.now() - timedelta(minutes=10), title="Test 1")
    private_event = event_factory(public_event=False, author=user, title="Test 1")

    url = f'/event/events/?title=Test 1'

    response = api_client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"
    assert response.data["count"] == 0
    assert len(response.data["results"]) == 0

@pytest.mark.django_db
def test_event_pagination(api_client, event_factory, user_factory):
    user = user_factory()

    event_factory.create_batch(21, author=user)

    url = '/event/events/'

    response = api_client.get(url, format="json")
    assert response.status_code == 200
    assert response.data["count"] == 21
    assert len(response.data["results"]) == 20
    assert response.data["next"] is not None

    url_page_2 = '/event/events/?page=2'
    
    response_page_2 = api_client.get(url_page_2, format="json")
    assert response_page_2.status_code == 200
    assert len(response_page_2.data["results"]) == 1
    assert response_page_2.data["previous"] is not None

@pytest.mark.django_db
def test_annon_see_events_details(api_client, event_factory, user_factory):
    user = user_factory()
    event = event_factory(author=user, title="Test", country="Polska", street_number="Jagiell")

    url = f'/event/events/{event.id}/'

    response = api_client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"

@pytest.mark.django_db
def test_private_event_see_details(api_client, event_factory, user_factory):
    user = user_factory()
    event = event_factory(author=user, title="Test", country="Polska", street_number="Jagiell", public_event=False)

    url = f'/event/events/{event.id}/'
    
    response = api_client.get(url, format="json")
    assert response.status_code == 404, f"Otrzymano błąd walidacji {response.data}"

    url2 = f'/event/events/9999999999/'
    response2 = api_client.get(url2, format="json")
    assert response2.status_code == 404, f"Otrzymano błąd walidacji {response.data}"
    
    assert response.data == response2.data

@pytest.mark.django_db
def test_private_event_see_details_author(auth_api_client, event_factory, user_factory):
    client, user = auth_api_client
    event = event_factory(author=user, title="Test", country="Polska", street_number="Jagiell", public_event=False)

    url = f'/event/events/{event.id}/'
    
    response = client.get(url, format="json")
    assert response.status_code == 200, f"Otrzymano błąd walidacji {response.data}"
    # print(response.data)

@pytest.mark.django_db
def test_creating_inv_in_event_author(auth_api_client, event_factory, user_factory):
    client, user = auth_api_client
    event = event_factory(author=user, public_event=False)

    url = f'/event/events/{event.id}/invitations/'

    payload = {
        "is_one_use": True,
        "is_active": True
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201, f"Blad {response.data}"
    inv = EventInvitation.objects.get()
    assert len(inv.code) == 8
    assert inv.is_active == True
    assert inv.is_one_use == True

@pytest.mark.django_db
def test_get_access_to_event_with_access_code(auth_api_client, event_factory, event_invitation_factory, user_factory):
    client, user = auth_api_client
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")
    inv = event_invitation_factory(event=event, created_by=user_author)

    access_code = inv.code
    url = f'/event/events/by-code/{access_code}/'

    response = client.get(url, format='json')
    assert response.status_code == 200, f"Blad {response.data}"
    event = Event.objects.get()
    assert event.title == "Testowo"

@pytest.mark.django_db
def test_get_access_to_event_with_access_code_bad_access(auth_api_client, event_factory, event_invitation_factory, user_factory):
    client, user = auth_api_client
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")
    inv = event_invitation_factory(event=event, created_by=user_author)

    access_code = 'BAS12345'
    url = f'/event/events/by-code/{access_code}/'

    response = client.get(url, format='json')
    assert response.status_code == 404, f"Blad {response.data}"

@pytest.mark.django_db
def test_get_access_to_event_with_access_code_code_used(auth_api_client, event_factory, event_invitation_factory, user_factory):
    client, user = auth_api_client
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")
    inv = event_invitation_factory(event=event, created_by=user_author, is_active=False)

    access_code = inv.code
    url = f'/event/events/by-code/{access_code}/'

    response = client.get(url, format='json')
    assert response.status_code == 404, f"Blad {response.data}"

@pytest.mark.django_db
def test_no_author_try_create_inv(auth_api_client, event_factory, event_invitation_factory, user_factory):
    client, user = auth_api_client
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")

    url = f'/event/events/{event.id}/invitations/'

    payload = {
        "is_one_use": True,
        "is_active": True
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 403, f"Blad {response.data}"
    inv = EventInvitation.objects.all()
    assert len(inv) == 0

@pytest.mark.django_db
def test_get_access_to_event_with_access_code(api_client, event_factory, event_invitation_factory, user_factory):
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")
    inv = event_invitation_factory(event=event, created_by=user_author)

    access_code = inv.code
    url = f'/event/events/by-code/{access_code}/'

    response = api_client.get(url, format='json')
    assert response.status_code == 401, f"Blad {response.data}"

@pytest.mark.django_db(transaction=True)
def test_two_users_use_same_invitation_code_at_the_same_time(auth_api_client, event_factory, event_invitation_factory, user_factory):
    user_author = user_factory()
    event = event_factory(author=user_author, public_event=False, title="Testowo")
    inv = event_invitation_factory(event=event, created_by=user_author, is_one_use=True)

    client1, user1 = auth_api_client 
    client2, user2  = auth_api_client

    url = f'/event/event-inv-join/'

    payload = {
        "code": inv.code
    }

    results = []

    def make_request(user, client):
        try:            
            response = client.post(url, payload)
            results.append(response.status_code)
        finally:
            connections.close_all()

    t1 = threading.Thread(target=make_request, args=(user1, client1))
    t2 = threading.Thread(target=make_request, args=(user2, client2))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert sorted(results) == [200, 400]

