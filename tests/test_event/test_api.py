import pytest
from django.utils import timezone
from datetime import timedelta
from event.models import Event
from .factories import EventFactory


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