import pytest
from decimal import Decimal
from diet.models import Product, DailyMealCalendar, MealCategory, MealItem, ProductServingUnit


@pytest.fixture
def sample_product():
    return Product.objects.create(
        title="Mleko 3.2%",
        kcal_1g=Decimal("0.60000"),
        protein_1g=Decimal("0.03000"),
        fat_1g=Decimal("0.03200"),
        carbohydrates_1g=Decimal("0.04800"),
        salt_1g=Decimal("0.00100"),
    )


@pytest.mark.django_db
def test_add_product_creates_day_and_meal_standard(auth_api_client, sample_product):
    client, user = auth_api_client

    url = "/diet/add-product/"
    payload = {
        "product_id": sample_product.id,
        "date": "2026-08-20",
        "meal_type": 1,
        "amount": 200.0,
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201, f"Otrzymano błąd: {response.data}"

    calendar = DailyMealCalendar.objects.filter(user=user, date="2026-08-20").first()
    assert calendar is not None

    meal = MealCategory.objects.filter(calendar=calendar, meal_type=1).first()
    assert meal is not None
    assert meal.name == "Śniadanie"

    item = MealItem.objects.filter(meal_category=meal, original_product=sample_product).first()
    assert item is not None
    assert float(item.calculated_gram_weight) == 200.0


@pytest.mark.django_db
def test_create_custom_meal_assigns_correct_meal_type(auth_api_client):
    client, user = auth_api_client

    url = "/diet/add-meal/"
    payload1 = {
        "date": "2026-08-20",
        "custom_name": "Podwieczorek 2",
    }
    response1 = client.post(url, payload1, format="json")
    assert response1.status_code == 201, f"Otrzymano błąd: {response1.data}"
    assert response1.data["meal_type"] == 6
    assert response1.data["name"] == "Podwieczorek 2"

    payload2 = {
        "date": "2026-08-20",
        "custom_name": "Przekąska nocna",
    }
    response2 = client.post(url, payload2, format="json")
    assert response2.status_code == 201, f"Otrzymano błąd: {response2.data}"
    assert response2.data["meal_type"] == 7
    assert response2.data["name"] == "Przekąska nocna"


@pytest.mark.django_db
def test_add_product_to_custom_meal(auth_api_client, sample_product):
    client, user = auth_api_client

    # Najpierw tworzymy posiłek custom
    create_meal_url = "/diet/add-meal/"
    create_res = client.post(create_meal_url, {"date": "2026-08-20", "custom_name": "Drugie śniadanie extra"}, format="json")
    assert create_res.status_code == 201
    custom_meal_type = create_res.data["meal_type"]

    # Następnie dodajemy produkt do tego posiłku custom (meal_type=6)
    add_product_url = "/diet/add-product/"
    payload = {
        "product_id": sample_product.id,
        "date": "2026-08-20",
        "meal_type": custom_meal_type,
        "amount": 150.0,
    }

    response = client.post(add_product_url, payload, format="json")
    assert response.status_code == 201, f"Otrzymano błąd: {response.data}"

    calendar = DailyMealCalendar.objects.get(user=user, date="2026-08-20")
    meal = MealCategory.objects.get(calendar=calendar, meal_type=custom_meal_type)
    assert meal.name == "Drugie śniadanie extra"
    assert MealItem.objects.filter(meal_category=meal, original_product=sample_product).exists()


@pytest.mark.django_db
def test_add_product_to_nonexistent_custom_meal_fails(auth_api_client, sample_product):
    client, user = auth_api_client

    url = "/diet/add-product/"
    payload = {
        "product_id": sample_product.id,
        "date": "2026-08-20",
        "meal_type": 6,  # Posiłek custom jeszcze nie istnieje!
        "amount": 100.0,
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "nie istnieje" in str(response.data)


@pytest.mark.django_db
def test_add_product_to_existing_meal(auth_api_client, sample_product):
    client, user = auth_api_client

    calendar = DailyMealCalendar.objects.create(user=user, date="2026-08-20")
    meal = MealCategory.objects.create(calendar=calendar, meal_type=3, name="Obiad", order=3)

    url = "/diet/add-product/"
    payload = {
        "product_id": sample_product.id,
        "date": "2026-08-20",
        "meal_type": 3,
        "amount": 100.0,
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201

    assert MealCategory.objects.filter(calendar=calendar, meal_type=3).count() == 1
    assert MealItem.objects.filter(meal_category=meal).count() == 1
