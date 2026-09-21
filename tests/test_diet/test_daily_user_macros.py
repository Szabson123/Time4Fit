import pytest
from decimal import Decimal
from diet.services import MacroCalculatorService
from user_profile.models import UserMacroProfile


# -------------------------------------------------------------------
# Unit Tests for MacroCalculatorService
# -------------------------------------------------------------------

def test_calculate_bmr_mifflin_male():
    # Weight: 80kg, Height: 180cm, Age: 25
    # BMR = 10*80 + 6.25*180 - 5*25 + 5 = 800 + 1125 - 125 + 5 = 1805.00
    bmr = MacroCalculatorService.calculate_bmr(
        gender="male",
        weight_kg=Decimal("80.00"),
        height_cm=Decimal("180.00"),
        age=25
    )
    assert bmr == Decimal("1805.00")


def test_calculate_bmr_mifflin_female():
    # Weight: 60kg, Height: 165cm, Age: 30
    # BMR = 10*60 + 6.25*165 - 5*30 - 161 = 600 + 1031.25 - 150 - 161 = 1320.25
    bmr = MacroCalculatorService.calculate_bmr(
        gender="female",
        weight_kg=Decimal("60.00"),
        height_cm=Decimal("165.00"),
        age=30
    )
    assert bmr == Decimal("1320.25")


def test_calculate_bmr_katch_mcardle_with_body_fat():
    # Weight: 80kg, BF: 15%
    # LBM = 80 * (1 - 0.15) = 68 kg
    # BMR = 370 + (21.6 * 68) = 370 + 1468.8 = 1838.80
    bmr = MacroCalculatorService.calculate_bmr(
        gender="male",
        weight_kg=Decimal("80.00"),
        height_cm=Decimal("180.00"),
        age=25,
        body_fat_percentage=Decimal("15.0")
    )
    assert bmr == Decimal("1838.80")


def test_calculate_tdee():
    bmr = Decimal("1800.00")
    # sedentary: 1.2 -> 2160.00
    assert MacroCalculatorService.calculate_tdee(bmr, "sedentary") == Decimal("2160.00")
    # lightly_active: 1.375 -> 2475.00
    assert MacroCalculatorService.calculate_tdee(bmr, "lightly_active") == Decimal("2475.00")
    # moderately_active: 1.55 -> 2790.00
    assert MacroCalculatorService.calculate_tdee(bmr, "moderately_active") == Decimal("2790.00")
    # very_active: 1.725 -> 3105.00
    assert MacroCalculatorService.calculate_tdee(bmr, "very_active") == Decimal("3105.00")


def test_calculate_target_macros_maintenance():
    tdee = Decimal("2000.00")
    weight_kg = Decimal("70.00")
    res = MacroCalculatorService.calculate_target_macros(tdee, "maintenance", weight_kg)

    assert res["target_calories"] == Decimal("2000.00")
    # Protein: 70 * 1.6 = 112g (448 kcal)
    assert res["target_protein_g"] == Decimal("112.00")
    # Fat: 25% of 2000 = 500 kcal / 9 = 55.56g (500.04 kcal)
    assert res["target_fat_g"] == Decimal("55.56")
    # Carbs: (2000 - 448 - 500.04) / 4 = 1051.96 / 4 = 262.99g
    assert res["target_carbohydrates_g"] == Decimal("262.99")


def test_calculate_target_macros_reduction():
    tdee = Decimal("2400.00")
    weight_kg = Decimal("80.00")
    res = MacroCalculatorService.calculate_target_macros(tdee, "reduction", weight_kg)

    # Reduction: 85% of 2400 = 2040 kcal
    assert res["target_calories"] == Decimal("2040.00")
    # Protein: 80 * 2.0 = 160g
    assert res["target_protein_g"] == Decimal("160.00")
    # Fat: 25% of 2040 = 510 kcal / 9 = 56.67g
    assert res["target_fat_g"] == Decimal("56.67")
    # Carbs: (2040 - 640 - 510.03) / 4 = 889.97 / 4 = 222.49g
    assert res["target_carbohydrates_g"] == Decimal("222.49")


def test_calculate_target_macros_muscle_gain():
    tdee = Decimal("2500.00")
    weight_kg = Decimal("75.00")
    res = MacroCalculatorService.calculate_target_macros(tdee, "muscle_gain", weight_kg)

    # Muscle gain: 110% of 2500 = 2750 kcal
    assert res["target_calories"] == Decimal("2750.00")
    # Protein: 75 * 1.8 = 135g
    assert res["target_protein_g"] == Decimal("135.00")


# -------------------------------------------------------------------
# Integration Tests for DailyUserMacrosView
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_unauthenticated_user_cannot_access_macros(api_client):
    response = api_client.get("/api/v1/diet/daily-user-macros/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_get_macros_when_not_configured_returns_404(auth_api_client):
    client, user = auth_api_client
    response = client.get("/api/v1/diet/daily-user-macros/")
    assert response.status_code == 404
    assert response.data["configured"] is False


@pytest.mark.django_db
def test_create_user_macros_post_success(auth_api_client):
    client, user = auth_api_client
    payload = {
        "gender": "male",
        "age": 28,
        "weight_kg": "80.00",
        "height_cm": "180.00",
        "body_fat_percentage": "15.0",
        "activity_level": "moderately_active",
        "goal": "reduction"
    }

    response = client.post("/api/v1/diet/daily-user-macros/", payload, format="json")
    assert response.status_code == 201
    data = response.data

    assert data["gender"] == "male"
    assert data["age"] == 28
    assert Decimal(str(data["weight_kg"])) == Decimal("80.00")
    assert Decimal(str(data["height_cm"])) == Decimal("180.00")
    assert Decimal(str(data["body_fat_percentage"])) == Decimal("15.0")
    assert data["activity_level"] == "moderately_active"
    assert data["goal"] == "reduction"

    # Verify calculated values exist and are positive
    assert Decimal(str(data["bmr"])) > 0
    assert Decimal(str(data["tdee"])) > 0
    assert Decimal(str(data["target_calories"])) > 0
    assert Decimal(str(data["target_protein_g"])) > 0
    assert Decimal(str(data["target_fat_g"])) > 0
    assert Decimal(str(data["target_carbohydrates_g"])) > 0

    # Verify DB persistence
    profile = UserMacroProfile.objects.get(user=user)
    assert profile.age == 28
    assert profile.goal == "reduction"
    assert profile.target_calories == Decimal(str(data["target_calories"]))


@pytest.mark.django_db
def test_get_macros_after_creation(auth_api_client):
    client, user = auth_api_client
    payload = {
        "gender": "female",
        "age": 26,
        "weight_kg": "62.00",
        "height_cm": "168.00",
        "activity_level": "lightly_active",
        "goal": "maintenance"
    }

    post_res = client.post("/api/v1/diet/daily-user-macros/", payload, format="json")
    assert post_res.status_code == 201

    # GET standard URL
    get_res = client.get("/api/v1/diet/daily-user-macros/")
    assert get_res.status_code == 200
    assert get_res.data["gender"] == "female"
    assert get_res.data["goal"] == "maintenance"
    assert get_res.data["body_fat_percentage"] is None


@pytest.mark.django_db
def test_dayly_user_macros_alias_works(auth_api_client):
    client, user = auth_api_client
    payload = {
        "gender": "male",
        "age": 30,
        "weight_kg": "75.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "muscle_gain"
    }

    # Use alias spelling with 'dayly'
    response = client.post("/api/v1/diet/dayly-user-macros/", payload, format="json")
    assert response.status_code == 201
    assert response.data["goal"] == "muscle_gain"

    get_alias = client.get("/api/v1/diet/dayly-user-macros/")
    assert get_alias.status_code == 200
    assert get_alias.data["goal"] == "muscle_gain"


@pytest.mark.django_db
def test_update_macros_via_put_recalculates(auth_api_client):
    client, user = auth_api_client
    initial = {
        "gender": "male",
        "age": 25,
        "weight_kg": "70.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "maintenance"
    }
    client.post("/api/v1/diet/daily-user-macros/", initial, format="json")

    # Update weight to 85kg and goal to reduction
    updated = {
        "gender": "male",
        "age": 25,
        "weight_kg": "85.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "reduction"
    }
    put_res = client.put("/api/v1/diet/daily-user-macros/", updated, format="json")
    assert put_res.status_code == 200
    assert Decimal(str(put_res.data["weight_kg"])) == Decimal("85.00")
    assert put_res.data["goal"] == "reduction"

    profile = UserMacroProfile.objects.get(user=user)
    assert profile.weight_kg == Decimal("85.00")
    assert profile.goal == "reduction"


@pytest.mark.django_db
def test_partial_update_via_patch_recalculates(auth_api_client):
    client, user = auth_api_client
    initial = {
        "gender": "male",
        "age": 25,
        "weight_kg": "70.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "maintenance"
    }
    post_res = client.post("/api/v1/diet/daily-user-macros/", initial, format="json")
    old_target_calories = Decimal(str(post_res.data["target_calories"]))

    # Change only activity_level to very_active
    patch_res = client.patch("/api/v1/diet/daily-user-macros/", {
        "activity_level": "very_active"
    }, format="json")
    assert patch_res.status_code == 200
    assert patch_res.data["activity_level"] == "very_active"
    new_target_calories = Decimal(str(patch_res.data["target_calories"]))
    assert new_target_calories > old_target_calories


@pytest.mark.django_db
def test_validation_errors(auth_api_client):
    client, user = auth_api_client

    # Invalid age (too low)
    res = client.post("/api/v1/diet/daily-user-macros/", {
        "gender": "male",
        "age": 5,
        "weight_kg": "70.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "maintenance"
    }, format="json")
    assert res.status_code == 400
    assert "age" in res.data

    # Invalid weight (negative)
    res = client.post("/api/v1/diet/daily-user-macros/", {
        "gender": "male",
        "age": 25,
        "weight_kg": "-10.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "maintenance"
    }, format="json")
    assert res.status_code == 400
    assert "weight_kg" in res.data

    # Invalid goal choice
    res = client.post("/api/v1/diet/daily-user-macros/", {
        "gender": "male",
        "age": 25,
        "weight_kg": "70.00",
        "height_cm": "175.00",
        "activity_level": "sedentary",
        "goal": "invalid_goal"
    }, format="json")
    assert res.status_code == 400
    assert "goal" in res.data
