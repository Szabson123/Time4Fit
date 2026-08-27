import pytest
from decimal import Decimal
from diet.models import (
    Product, ProductCategory, ProductAdditionalInfo,
    ProductServingUnit, ProductDescription, Dish, DishIngredient, DishCategory
)


@pytest.fixture
def complex_product():
    cat = ProductCategory.objects.create(name="Pieczywo")
    product = Product.objects.create(
        title="Chleb Żytni Bio",
        brand="Piekarnia Natura",
        barcode="5901234567890",
        quantity_display="500g",
        category=cat,
        nutriscore="A",
        nova_group=2,
        allergens=["gluten"],
        countries=["poland", "germany"],
        package_name="Bochenek",
        package_whole_g=Decimal("500.00"),
        kcal_1g=Decimal("2.40000"),
        protein_1g=Decimal("0.08000"),
        fat_1g=Decimal("0.01500"),
        carbohydrates_1g=Decimal("0.48000"),
        salt_1g=Decimal("0.01200"),
        sugars_1g=Decimal("0.02500"),
        saturated_fat_1g=Decimal("0.00300"),
        fiber_1g=Decimal("0.07000"),
    )

    ProductAdditionalInfo.objects.create(
        product=product,
        is_vegan=True,
        is_vegetarian=True,
        is_palm_oil_free=True,
        is_complete_profile=True,
        ingredients_text="Mąka żytnia, woda, zakwas, sól",
        traces=["sesame"],
        labels=["bio", "organic"],
        additives_tags=[],
    )

    ProductDescription.objects.create(
        product=product,
        language="pl",
        description="Tradycyjny chleb żytni na naturalnym zakwasie."
    )

    ProductDescription.objects.create(
        product=product,
        language="en",
        description="Traditional rye bread made with natural sourdough."
    )

    ProductServingUnit.objects.create(
        product=product,
        unit_name="slice",
        custom_label="Kromka (35g)",
        gram_weight=Decimal("35.00"),
        is_global=True,
    )

    # Dish using this product
    dish_cat = DishCategory.objects.create(name="Śniadanie")
    dish = Dish.objects.create(
        name="Kanapka z awokado",
        category=dish_cat,
    )
    DishIngredient.objects.create(
        dish=dish,
        product=product,
        weight_in_g=Decimal("70.00")
    )

    return product


@pytest.mark.django_db
def test_get_product_detail_by_id(auth_api_client, complex_product):
    client, user = auth_api_client

    url = f"/api/v1/diet/products/{complex_product.id}/"
    response = client.get(url)
    assert response.status_code == 200

    data = response.data
    assert data["id"] == complex_product.id
    assert data["title"] == "Chleb Żytni Bio"
    assert data["brand"] == "Piekarnia Natura"
    assert data["barcode"] == "5901234567890"
    assert data["category_name"] == "Pieczywo"
    assert data["nutriscore"] == "A"
    assert data["nova_group"] == 2
    assert data["countries"] == ["poland", "germany"]
    assert data["allergens"] == ["gluten"]
    assert data["package_name"] == "Bochenek"
    assert float(data["package_whole_g"]) == 500.0

    # Default description (Polish)
    assert data["product_desc"] == "Tradycyjny chleb żytni na naturalnym zakwasie."

    # Nutrition per 100g
    assert float(data["kcal_100g"]) == 240.0
    assert float(data["protein_100g"]) == 8.0
    assert float(data["fat_100g"]) == 1.5
    assert float(data["carbohydrates_100g"]) == 48.0
    assert float(data["salt_100g"]) == 1.2
    assert float(data["sugars_100g"]) == 2.5
    assert float(data["saturated_fat_100g"]) == 0.3
    assert float(data["fiber_100g"]) == 7.0

    # Additional info
    info = data["additional_info"]
    assert info["is_vegan"] is True
    assert info["is_vegetarian"] is True
    assert info["is_palm_oil_free"] is True
    assert "bio" in info["labels"]
    assert "sesame" in info["traces"]
    assert "Mąka żytnia" in info["ingredients_text"]

    # Serving units
    assert len(data["serving_units"]) == 1
    assert data["serving_units"][0]["label"] == "Kromka (35g)"

    # Recipes
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["name"] == "Kanapka z awokado"
    assert data["recipes"][0]["category"] == "Śniadanie"


@pytest.mark.django_db
def test_get_product_detail_by_barcode(auth_api_client, complex_product):
    client, user = auth_api_client

    url = f"/api/v1/diet/products/barcode/{complex_product.barcode}/"
    response = client.get(url)
    assert response.status_code == 200

    data = response.data
    assert data["id"] == complex_product.id
    assert data["barcode"] == complex_product.barcode
    assert data["title"] == complex_product.title


@pytest.mark.django_db
def test_get_product_detail_language_selection(auth_api_client, complex_product):
    client, user = auth_api_client

    # Request English description via query param
    url = f"/api/v1/diet/products/{complex_product.id}/?lang=en"
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["product_desc"] == "Traditional rye bread made with natural sourdough."

    # Request nonexistent language (fallback to pl)
    url_de = f"/api/v1/diet/products/{complex_product.id}/?lang=de"
    res_de = client.get(url_de)
    assert res_de.status_code == 200
    assert res_de.data["product_desc"] == "Tradycyjny chleb żytni na naturalnym zakwasie."


@pytest.mark.django_db
def test_get_minimal_product_detail(auth_api_client):
    client, user = auth_api_client

    minimal = Product.objects.create(
        title="Woda Źródlana",
        kcal_1g=Decimal("0.00000"),
        protein_1g=Decimal("0.00000"),
        fat_1g=Decimal("0.00000"),
        carbohydrates_1g=Decimal("0.00000"),
        salt_1g=Decimal("0.00000"),
    )

    url = f"/api/v1/diet/products/{minimal.id}/"
    response = client.get(url)
    assert response.status_code == 200

    data = response.data
    assert data["id"] == minimal.id
    assert data["product_desc"] is None
    assert data["brand"] is None
    assert data["additional_info"] is None
    assert data["recipes"] == []
    assert data["serving_units"] == []
    assert data["sugars_100g"] is None
    assert data["fiber_100g"] is None


@pytest.mark.django_db
def test_get_product_detail_increments_popularity(auth_api_client, complex_product):
    client, user = auth_api_client
    from diet.tasks import increment_product_popularity

    assert complex_product.popularity is None

    # Simulating task execution when user views product detail (+2 points)
    increment_product_popularity(complex_product.id, points=2)
    complex_product.refresh_from_db()
    assert complex_product.popularity == 2

    # View again (+2 points)
    increment_product_popularity(complex_product.id, points=2)
    complex_product.refresh_from_db()
    assert complex_product.popularity == 4
