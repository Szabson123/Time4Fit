import pytest
from decimal import Decimal
from diet.models import Product, DailyMealCalendar, MealCategory, MealItem


@pytest.mark.django_db
def test_quick_add_creates_meal_item_snapshot_without_product(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-20"

    initial_product_count = Product.objects.count()

    # 1. Quick add to Lunch (meal_type 3)
    response = client.post("/api/v1/diet/quick-add/", {
        "date": date_str,
        "meal_type": 3,
        "name": "Obiad w restauracji",
        "kcal": 650.0,
        "protein": 35.0,
        "carbohydrates": 70.0,
        "fat": 20.0,
        "salt": 1.5,
    }, format="json")

    assert response.status_code == 201
    data = response.data
    assert data["name"] == "Obiad w restauracji"
    assert float(data["total_kcal"]) == 650.0
    assert float(data["total_protein"]) == 35.0
    assert float(data["total_carbohydrates"]) == 70.0
    assert float(data["total_fat"]) == 20.0
    assert float(data["display_salt"]) == 1.5
    assert data["is_quick_add"] is True

    # Crucial check: NO product was created in catalog
    assert Product.objects.count() == initial_product_count

    # Check that MealItem in DB has original_product=None
    meal_item = MealItem.objects.get(id=data["id"])
    assert meal_item.original_product is None
    assert meal_item.original_recipe is None
    assert meal_item.is_quick_add is True

    # 2. Check daily-meals endpoint includes this snapshot in lunch and day totals
    res_calendar = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_calendar.status_code == 200
    cal_data = res_calendar.data

    assert float(cal_data["total_day_kcal"]) == 650.0
    assert float(cal_data["total_day_protein"]) == 35.0
    assert float(cal_data["total_day_carbohydrates"]) == 70.0
    assert float(cal_data["total_day_fat"]) == 20.0
    assert float(cal_data["total_day_salt"]) == 1.5

    # Check slot 3 (Obiad)
    lunch_slot = cal_data["meals"][2]
    assert lunch_slot["meal_type"] == 3
    assert float(lunch_slot["category_kcal"]) == 650.0
    assert float(lunch_slot["category_protein"]) == 35.0
    assert float(lunch_slot["category_carbohydrates"]) == 70.0
    assert float(lunch_slot["category_fat"]) == 20.0
    assert float(lunch_slot["category_salt"]) == 1.5
    assert len(lunch_slot["direct_items"]) == 1
    assert lunch_slot["direct_items"][0]["name"] == "Obiad w restauracji"
    assert lunch_slot["direct_items"][0]["is_quick_add"] is True


@pytest.mark.django_db
def test_quick_add_default_name_and_zero_macros(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-20"

    # Only provide kcal, no name or other macros
    res = client.post("/api/v1/diet/quick-add/", {
        "date": date_str,
        "meal_type": 1,
        "kcal": 200.0,
    }, format="json")

    assert res.status_code == 201
    assert res.data["name"] == "Szybkie dodanie"
    assert float(res.data["total_kcal"]) == 200.0
    assert float(res.data["total_protein"]) == 0.0
    assert float(res.data["total_carbohydrates"]) == 0.0
    assert float(res.data["total_fat"]) == 0.0
    assert float(res.data["display_salt"]) == 0.0
    assert res.data["is_quick_add"] is True


@pytest.mark.django_db
def test_quick_add_custom_meal_type_validation(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-20"

    # Meal 6 doesn't exist yet -> 400
    res_bad = client.post("/api/v1/diet/quick-add/", {
        "date": date_str,
        "meal_type": 6,
        "kcal": 150.0,
    }, format="json")
    assert res_bad.status_code == 400

    # Create custom meal 6 first
    client.post("/api/v1/diet/add-meal/", {
        "date": date_str,
        "custom_name": "Przekąska",
    }, format="json")

    # Now quick add to meal 6 succeeds
    res_good = client.post("/api/v1/diet/quick-add/", {
        "date": date_str,
        "meal_type": 6,
        "kcal": 150.0,
    }, format="json")
    assert res_good.status_code == 201
    assert float(res_good.data["total_kcal"]) == 150.0
