import pytest
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from diet.models import Product, ProductServingUnit, ProductAdditionalInfo


@pytest.mark.django_db
def test_create_product_full_json(auth_api_client):
    client, user = auth_api_client

    payload = {
        "title": "Twaróg półtłusty",
        "brand": "Piątnica",
        "barcode": "5900138023412",
        "values_per": 100.0,
        "kcal": 104.0,
        "protein": 12.4,
        "carbohydrates": 3.8,
        "fat": 4.6,
        "salt": 0.18,
        "package_name": "Kubek plastikowy",
        "package_whole_g": 250.0,
        "ingredients_text": "Mleko pasteryzowane, kultury bakterii kwaszących",
        "allergens": ["Mleko i produkty mleczne"],
        "traces": ["Soja"],
        "countries": ["Polska"],
        "serving_units": [
            {"unit_name": "cup", "custom_label": "Szklanka", "gram_weight": 250.0},
            {"unit_name": "serving", "custom_label": "Porcja", "gram_weight": 100.0}
        ]
    }

    response = client.post("/api/v1/diet/products/", payload, format="json")
    assert response.status_code == 201
    data = response.data

    assert data["title"] == "Twaróg półtłusty"
    assert data["brand"] == "Piątnica"
    assert data["barcode"] == "5900138023412"
    assert data["package_name"] == "Kubek plastikowy"
    assert float(data["package_whole_g"]) == 250.0
    assert float(data["kcal_100g"]) == 104.0
    assert float(data["protein_100g"]) == 12.4
    assert float(data["carbohydrates_100g"]) == 3.8
    assert float(data["fat_100g"]) == 4.6
    assert float(data["salt_100g"]) == 0.18

    # Serving units
    assert len(data["serving_units"]) == 2
    labels = [su["label"] for su in data["serving_units"]]
    assert "Szklanka" in labels
    assert "Porcja" in labels

    # Additional info
    assert data["additional_info"]["ingredients_text"] == "Mleko pasteryzowane, kultury bakterii kwaszących"
    assert "Soja" in data["additional_info"]["traces"]

    # Verify DB record
    product = Product.objects.get(id=data["id"])
    assert product.user == user
    assert product.kcal_1g == Decimal("1.04000")
    assert product.protein_1g == Decimal("0.12400")
    assert product.fat_1g == Decimal("0.04600")
    assert product.carbohydrates_1g == Decimal("0.03800")
    assert product.salt_1g == Decimal("0.00180")

    # Verify ProductServingUnit in DB
    assert ProductServingUnit.objects.filter(product=product).count() == 2

    # Verify searchable in ProductListView for this user
    res_list = client.get("/api/v1/diet/products/?search=Twaróg")
    assert res_list.status_code == 200
    assert any(p["id"] == product.id for p in res_list.data)

    # Verify retrieve detail
    res_detail = client.get(f"/api/v1/diet/products/{product.id}/")
    assert res_detail.status_code == 200
    assert res_detail.data["title"] == "Twaróg półtłusty"


@pytest.mark.django_db
def test_create_product_with_image_and_ingredients_image_multipart(auth_api_client):
    client, user = auth_api_client

    # Create dummy images
    dummy_image = SimpleUploadedFile(
        name="product.jpg",
        content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
        content_type="image/gif"
    )
    dummy_ingredients_image = SimpleUploadedFile(
        name="ingredients.jpg",
        content=b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
        content_type="image/gif"
    )

    multipart_data = {
        "title": "Baton Proteinowy",
        "brand": "FitBar",
        "barcode": "5901234567890",
        "values_per": "100.00",
        "kcal": "380.0",
        "protein": "30.0",
        "carbohydrates": "35.0",
        "fat": "12.0",
        "salt": "0.5",
        "ingredients_text": "Białka serwatkowe, płatki owsiane",
        "allergens": '["Mleko", "Owies"]',
        "traces": '["Orzeszki ziemne"]',
        "serving_units": '[{"custom_label": "1 baton", "gram_weight": 50.0}]',
        "image": dummy_image,
        "ingredients_image": dummy_ingredients_image,
    }

    response = client.post("/api/v1/diet/products/", multipart_data, format="multipart")
    assert response.status_code == 201
    data = response.data

    assert data["title"] == "Baton Proteinowy"
    assert data["image"] is not None
    assert data["ingredients_image"] is not None

    product = Product.objects.get(id=data["id"])
    assert bool(product.image) is True
    assert bool(product.ingredients_image) is True
    assert product.user == user


@pytest.mark.django_db
def test_create_product_alias_endpoint(auth_api_client):
    client, user = auth_api_client

    payload = {
        "title": "Sok jabłkowy",
        "kcal": 45.0,
        "protein": 0.1,
        "carbohydrates": 11.0,
        "fat": 0.1,
        "salt": 0.01,
    }

    # Test via /products/create/ alias
    response = client.post("/api/v1/diet/products/create/", payload, format="json")
    assert response.status_code == 201
    assert response.data["title"] == "Sok jabłkowy"
