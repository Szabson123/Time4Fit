import pytest
from decimal import Decimal
from diet.models import Product, DailyMealCalendar, MealCategory, MealItem


@pytest.fixture
def sample_product():
    return Product.objects.create(
        title="Owsianka",
        kcal_1g=Decimal("3.80000"),
        protein_1g=Decimal("0.13000"),
        fat_1g=Decimal("0.07000"),
        carbohydrates_1g=Decimal("0.65000"),
        salt_1g=Decimal("0.00200"),
    )


@pytest.mark.django_db
def test_get_daily_meals_for_nonexistent_day_does_not_create_db_record(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-08-27"

    response = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert response.status_code == 200

    # Ensure no DailyMealCalendar or MealCategory records were created in DB
    assert DailyMealCalendar.objects.filter(user=user, date=date_str).exists() is False
    assert MealCategory.objects.count() == 0

    data = response.data
    assert data["id"] is None
    assert data["date"] == date_str
    assert data["total_day_kcal"] == "0.00"
    assert data["total_day_protein"] == "0.00"
    assert data["total_day_fat"] == "0.00"
    assert data["total_day_carbohydrates"] == "0.00"
    assert data["total_day_salt"] == "0.00"

    meals = data["meals"]
    assert len(meals) == 5

    for idx, meal in enumerate(meals, start=1):
        assert meal["id"] is None
        assert meal["meal_type"] == idx
        assert meal["name"] is None
        assert meal["order"] == idx
        assert meal["category_kcal"] == "0.00"
        assert meal["category_protein"] == "0.00"
        assert meal["category_fat"] == "0.00"
        assert meal["category_carbohydrates"] == "0.00"
        assert meal["category_salt"] == "0.00"
        assert meal["full_meals"] == []
        assert meal["direct_items"] == []


@pytest.mark.django_db
def test_get_daily_meals_partially_filled_day_fills_missing_slots(auth_api_client, sample_product):
    client, user = auth_api_client
    date_str = "2026-08-27"

    # User adds product to meal 1 (Śniadanie)
    add_product_url = "/api/v1/diet/add-product/"
    add_res = client.post(add_product_url, {
        "product_id": sample_product.id,
        "date": date_str,
        "meal_type": 1,
        "amount": 100.0,
    }, format="json")
    assert add_res.status_code == 201

    # In DB, only meal_type=1 exists
    calendar = DailyMealCalendar.objects.get(user=user, date=date_str)
    assert calendar.meals.count() == 1

    # Fetch daily meals
    res = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res.status_code == 200
    data = res.data

    assert data["id"] == calendar.id
    assert data["date"] == date_str
    assert float(data["total_day_kcal"]) == 380.0
    assert float(data["total_day_protein"]) == 13.0
    assert float(data["total_day_fat"]) == 7.0
    assert float(data["total_day_carbohydrates"]) == 65.0

    meals = data["meals"]
    assert len(meals) == 5

    # Meal 1 has data and id
    meal1 = meals[0]
    assert meal1["id"] is not None
    assert meal1["meal_type"] == 1
    assert meal1["name"] is None
    assert float(meal1["category_kcal"]) == 380.0
    assert len(meal1["direct_items"]) == 1
    assert meal1["direct_items"][0]["name"] == "Owsianka"

    # Meals 2..5 are empty dummy slots
    for idx in range(1, 5):
        meal = meals[idx]
        assert meal["id"] is None
        assert meal["meal_type"] == idx + 1
        assert meal["name"] is None
        assert meal["category_kcal"] == "0.00"
        assert meal["direct_items"] == []
        assert meal["full_meals"] == []

    # Verify DB still only has 1 MealCategory
    assert calendar.meals.count() == 1


@pytest.mark.django_db
def test_get_daily_meals_with_custom_meals(auth_api_client, sample_product):
    client, user = auth_api_client
    date_str = "2026-08-27"

    # Create custom meal 1 (meal_type 6)
    res_custom1 = client.post("/api/v1/diet/add-meal/", {
        "date": date_str,
        "custom_name": "Przekąska przedtreningowa",
    }, format="json")
    assert res_custom1.status_code == 201
    assert res_custom1.data["meal_type"] == 6
    assert res_custom1.data["name"] == "Przekąska przedtreningowa"

    # Create custom meal 2 (meal_type 7)
    res_custom2 = client.post("/api/v1/diet/add-meal/", {
        "date": date_str,
        "custom_name": "Nocna przekąska",
    }, format="json")
    assert res_custom2.status_code == 201
    assert res_custom2.data["meal_type"] == 7
    assert res_custom2.data["name"] == "Nocna przekąska"

    # Add product to meal 6
    client.post("/api/v1/diet/add-product/", {
        "product_id": sample_product.id,
        "date": date_str,
        "meal_type": 6,
        "amount": 50.0,
    }, format="json")

    # Fetch daily meals
    res = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res.status_code == 200
    data = res.data

    meals = data["meals"]
    # 5 standard slots + 2 custom meals = 7 meals
    assert len(meals) == 7

    # 1..5 standard slots (all empty because user only added to 6)
    for i in range(5):
        assert meals[i]["meal_type"] == i + 1
        assert meals[i]["name"] is None
        assert meals[i]["id"] is None
        assert meals[i]["category_kcal"] == "0.00"

    # 6th meal (custom)
    meal6 = meals[5]
    assert meal6["meal_type"] == 6
    assert meal6["name"] == "Przekąska przedtreningowa"
    assert meal6["id"] is not None
    assert float(meal6["category_kcal"]) == 190.0
    assert len(meal6["direct_items"]) == 1

    # 7th meal (custom)
    meal7 = meals[6]
    assert meal7["meal_type"] == 7
    assert meal7["name"] == "Nocna przekąska"
    assert meal7["id"] is not None
    assert float(meal7["category_kcal"]) == 0.0
    assert len(meal7["direct_items"]) == 0


@pytest.mark.django_db
def test_get_daily_meals_bad_date(auth_api_client):
    client, user = auth_api_client

    # Missing date parameter
    res1 = client.get("/api/v1/diet/daily-meals/")
    assert res1.status_code == 400

    # Invalid date format
    res2 = client.get("/api/v1/diet/daily-meals/?date=invalid-date")
    assert res2.status_code == 400
