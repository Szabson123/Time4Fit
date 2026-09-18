import pytest
from decimal import Decimal
from diet.models import DailyMealCalendar, Product


@pytest.mark.django_db
def test_add_water_default_amount_click(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-13"

    # 1. First button click: adds default 250ml
    response = client.post("/api/v1/diet/water/", {
        "date": date_str
    }, format="json")

    assert response.status_code == 200
    assert response.data["date"] == date_str
    assert response.data["water_intake_ml"] == 250
    assert response.data["standard_water_intake_ml"] == 250
    assert response.data["daily_water_goal_ml"] == 2000

    # Verify DB record
    calendar_day = DailyMealCalendar.objects.get(user=user, date=date_str)
    assert calendar_day.water_intake_ml == 250

    # 2. Second button click: adds another 250ml -> 500ml
    response2 = client.post("/api/v1/diet/water/", {
        "date": date_str
    }, format="json")

    assert response2.status_code == 200
    assert response2.data["water_intake_ml"] == 500

    calendar_day.refresh_from_db()
    assert calendar_day.water_intake_ml == 500


@pytest.mark.django_db
def test_add_water_uses_updated_profile_settings(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-13"

    # Update profile standard water intake to 330ml and goal to 2500ml
    settings_res = client.patch("/api/v1/user/settings/", {
        "standard_water_intake_ml": 330,
        "daily_water_goal_ml": 2500
    }, format="json")
    assert settings_res.status_code == 200
    assert settings_res.data["standard_water_intake_ml"] == 330
    assert settings_res.data["daily_water_goal_ml"] == 2500

    # Click button to add water without passing amount_ml
    response = client.post("/api/v1/diet/water/", {
        "date": date_str
    }, format="json")

    assert response.status_code == 200
    assert response.data["water_intake_ml"] == 330
    assert response.data["standard_water_intake_ml"] == 330
    assert response.data["daily_water_goal_ml"] == 2500


@pytest.mark.django_db
def test_water_actions_subtract_set_reset_and_custom_amount(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-13"

    # Custom amount 500ml
    res = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 500,
        "action": "add"
    }, format="json")
    assert res.status_code == 200
    assert res.data["water_intake_ml"] == 500

    # Subtract 200ml -> 300ml
    res_sub = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 200,
        "action": "subtract"
    }, format="json")
    assert res_sub.status_code == 200
    assert res_sub.data["water_intake_ml"] == 300

    # Subtract 500ml -> should not drop below 0
    res_sub_below = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 500,
        "action": "subtract"
    }, format="json")
    assert res_sub_below.status_code == 200
    assert res_sub_below.data["water_intake_ml"] == 0

    # Set exact 1200ml
    res_set = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 1200,
        "action": "set"
    }, format="json")
    assert res_set.status_code == 200
    assert res_set.data["water_intake_ml"] == 1200

    # Reset
    res_reset = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "action": "reset"
    }, format="json")
    assert res_reset.status_code == 200
    assert res_reset.data["water_intake_ml"] == 0


@pytest.mark.django_db
def test_get_daily_water_intake(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-13"

    # When no water record exists yet
    res = client.get(f"/api/v1/diet/water/?date={date_str}")
    assert res.status_code == 200
    assert res.data["date"] == date_str
    assert res.data["water_intake_ml"] == 0
    assert res.data["standard_water_intake_ml"] == 250

    # Add water
    client.post("/api/v1/diet/water/", {"date": date_str}, format="json")

    # Fetch again
    res2 = client.get(f"/api/v1/diet/water/?date={date_str}")
    assert res2.status_code == 200
    assert res2.data["water_intake_ml"] == 250


@pytest.mark.django_db
def test_daily_meal_calendar_returns_water_and_kcal_together(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-13"

    # 1. Nonexistent day -> returns water_intake_ml 0 along with kcal 0.00 and empty water_glasses
    res_empty = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_empty.status_code == 200
    assert res_empty.data["total_day_kcal"] == "0.00"
    assert res_empty.data["water_intake_ml"] == 0
    assert res_empty.data["standard_water_intake_ml"] == 250
    assert res_empty.data["daily_water_goal_ml"] == 2000
    assert res_empty.data["water_glasses"] == []

    # 2. Add water only (button click)
    res_post = client.post("/api/v1/diet/water/", {"date": date_str}, format="json")
    assert res_post.status_code == 200
    assert len(res_post.data["water_glasses"]) == 1
    assert res_post.data["water_glasses"][0]["amount_ml"] == 250

    # Calendar endpoint should now return 250ml water, 0.00 kcal, 5 empty meal slots, and 1 glass
    res_water_only = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_water_only.status_code == 200
    assert res_water_only.data["id"] is not None
    assert res_water_only.data["water_intake_ml"] == 250
    assert float(res_water_only.data["total_day_kcal"]) == 0.0
    assert len(res_water_only.data["meals"]) == 5
    assert len(res_water_only.data["water_glasses"]) == 1
    assert res_water_only.data["water_glasses"][0]["amount_ml"] == 250

    # 3. Add a food product to breakfast
    product = Product.objects.create(
        title="Jajko",
        kcal_1g=Decimal("1.40000"),
        protein_1g=Decimal("0.12000"),
        fat_1g=Decimal("0.10000"),
        carbohydrates_1g=Decimal("0.01000"),
        salt_1g=Decimal("0.00300"),
    )
    client.post("/api/v1/diet/add-product/", {
        "product_id": product.id,
        "date": date_str,
        "meal_type": 1,
        "amount": 100.0,
    }, format="json")

    # Add another glass of water
    client.post("/api/v1/diet/water/", {"date": date_str}, format="json")

    # Calendar endpoint returns combined kcal, nutrients, meals, and water glasses!
    res_combined = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_combined.status_code == 200
    assert float(res_combined.data["total_day_kcal"]) == 140.0
    assert res_combined.data["water_intake_ml"] == 500
    assert res_combined.data["standard_water_intake_ml"] == 250
    assert res_combined.data["daily_water_goal_ml"] == 2000
    assert len(res_combined.data["water_glasses"]) == 2
    assert res_combined.data["water_glasses"][0]["amount_ml"] == 250
    assert res_combined.data["water_glasses"][1]["amount_ml"] == 250


@pytest.mark.django_db
def test_water_glasses_detail_and_deletion(auth_api_client):
    client, user = auth_api_client
    date_str = "2026-09-14"

    # Add first glass 250ml
    res1 = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 250
    }, format="json")
    assert res1.status_code == 200
    glass1_id = res1.data["water_glasses"][0]["id"]

    # Add second glass 350ml
    res2 = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "amount_ml": 350
    }, format="json")
    assert res2.status_code == 200
    assert len(res2.data["water_glasses"]) == 2
    glass2_id = res2.data["water_glasses"][1]["id"]

    # Check daily-meals endpoint returns both glasses
    res_meals = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_meals.status_code == 200
    assert res_meals.data["water_intake_ml"] == 600
    assert len(res_meals.data["water_glasses"]) == 2
    assert res_meals.data["water_glasses"][0]["id"] == glass1_id
    assert res_meals.data["water_glasses"][0]["amount_ml"] == 250
    assert res_meals.data["water_glasses"][1]["id"] == glass2_id
    assert res_meals.data["water_glasses"][1]["amount_ml"] == 350

    # Delete glass 1 via action='delete'
    res_del1 = client.post("/api/v1/diet/water/", {
        "date": date_str,
        "action": "delete",
        "glass_id": glass1_id
    }, format="json")
    assert res_del1.status_code == 200
    assert res_del1.data["water_intake_ml"] == 350
    assert len(res_del1.data["water_glasses"]) == 1
    assert res_del1.data["water_glasses"][0]["id"] == glass2_id

    # Verify daily-meals after deleting glass 1
    res_meals_after1 = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_meals_after1.data["water_intake_ml"] == 350
    assert len(res_meals_after1.data["water_glasses"]) == 1

    # Delete glass 2 via DELETE HTTP method
    res_del2 = client.delete(f"/api/v1/diet/water/?date={date_str}&glass_id={glass2_id}")
    assert res_del2.status_code == 200
    assert res_del2.data["water_intake_ml"] == 0
    assert len(res_del2.data["water_glasses"]) == 0

    # Verify daily-meals after deleting glass 2
    res_meals_after2 = client.get(f"/api/v1/diet/daily-meals/?date={date_str}")
    assert res_meals_after2.data["water_intake_ml"] == 0
    assert res_meals_after2.data["water_glasses"] == []

