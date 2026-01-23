import pytest
from django.utils import timezone
from datetime import timedelta
from event.models import Event, EventInvitation
from .factories import EventFactory
import threading
from django.db import connections
from rest_framework.test import APIClient


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
    
    public_event2 = event_factory(author=user, date_time_event=timezone.now() - timedelta(minutes=10), title="Test 1", public_event=True)
    private_event = event_factory(public_event=False, author=user, title="Test 1", date_time_event=timezone.now() + timedelta(days=1))

    url = f'/event/events/?title=Test 1'

    response = api_client.get(url, format="json")
    
    assert response.status_code == 200
    assert response.data["count"] == 0

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
def test_two_users_use_same_invitation_code_at_the_same_time(event_factory, event_invitation_factory, user_factory):
    author = user_factory()
    event = event_factory(author=author, public_event=False)

    invitation = event_invitation_factory(
        event=event,
        created_by=author,
        is_one_use=True
    )

    user1 = user_factory()
    user2 = user_factory()

    client1 = APIClient()
    client1.force_authenticate(user=user1)

    client2 = APIClient()
    client2.force_authenticate(user=user2)

    url = '/event/event-inv-join/'

    payload = {
        "code": invitation.code
    }

    results = []
    barrier = threading.Barrier(2)

    def make_request(client):
        try:
            barrier.wait()
            response = client.post(url, payload, format="json")
            results.append(response.status_code)
        finally:
            connections.close_all() 

    t1 = threading.Thread(target=make_request, args=(client1,))
    t2 = threading.Thread(target=make_request, args=(client2,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    connections.close_all()

    assert sorted(results) == [200, 400]

@pytest.mark.django_db
def test_deleting_user_from_participant_list_happy_path(auth_api_client, event_factory, user_factory, event_participant_factory):
    client, user = auth_api_client
    event = event_factory(author=user, public_event=False)

    user_participant = user_factory()
    event_participant = event_participant_factory(
        event=event,
        user=user_participant
    )

    url = f'/event/{event.id}/event-participant-list/{event_participant.id}/delete_user_from_participant_list/'

    response = client.post(url, format="json")
    print(response)
    assert response.status_code == 204

@pytest.mark.django_db
def test_deleting_user_from_participant_list_perm_denied(auth_api_client, event_factory, user_factory, event_participant_factory):
    client, user = auth_api_client
    random_user = user_factory()
    event = event_factory(author=random_user, public_event=False)

    user_participant = user_factory()
    event_participant = event_participant_factory(
        event=event,
        user=user_participant
    )

    url = f'/event/{event.id}/event-participant-list/{event_participant.id}/delete_user_from_participant_list/'

    response = client.post(url, format="json")
    assert response.status_code == 403, f'blad {response.data}'

@pytest.mark.django_db
def test_author_can_kick_user_and_user_loses_access(auth_api_client, user_factory, event_factory, event_participant_factory):
    client, author = auth_api_client

    kicked_user = user_factory()
    client2 = APIClient()
    client2.force_authenticate(user=kicked_user)

    event = event_factory(author=author, public_event=False)

    event_participant = event_participant_factory(event=event, user=kicked_user)

    url = f'/event/{event.id}/event-participant-list/{event_participant.id}/delete_user_from_participant_list/'

    response = client.post(url)
    assert response.status_code == 204

    event_url = f'/event/events/{event.id}/'
    response = client2.get(event_url)
    assert response.status_code == 404

@pytest.mark.django_db
def test_join_to_public_event_happy_path(auth_api_client, user_factory, event_factory):
    client, user = auth_api_client
    author = user_factory()
    event = event_factory(author=author, public_event=True)

    url = f'/event/events/{event.id}/join_to_public_event/'
    response = client.post(url)

    assert response.status_code == 200, f'blad {response.data}'