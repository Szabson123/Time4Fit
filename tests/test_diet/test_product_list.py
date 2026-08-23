import pytest
from decimal import Decimal
from diet.models import Product, ProductServingUnit


@pytest.mark.django_db
def test_product_list_returns_only_global_products(auth_api_client):
    client, user = auth_api_client

    # Produkty globalne (user is null)
    global_p1 = Product.objects.create(
        title="Banan",
        kcal_1g=Decimal("0.89000"),
        protein_1g=Decimal("0.01100"),
        fat_1g=Decimal("0.00300"),
        carbohydrates_1g=Decimal("0.23000"),
        user=None,
    )
    global_p2 = Product.objects.create(
        title="Jabłko",
        kcal_1g=Decimal("0.52000"),
        protein_1g=Decimal("0.00300"),
        fat_1g=Decimal("0.00200"),
        carbohydrates_1g=Decimal("0.14000"),
        user=None,
    )

    # Produkt użytkownika (powinien być wykluczony)
    Product.objects.create(
        title="Mój prywatny posiłek",
        kcal_1g=Decimal("1.50000"),
        protein_1g=Decimal("0.10000"),
        fat_1g=Decimal("0.05000"),
        carbohydrates_1g=Decimal("0.20000"),
        user=user,
    )

    url = "/diet/products/"
    response = client.get(url)
    assert response.status_code == 200

    results = response.data.get("results", response.data)
    assert len(results) == 2
    titles = [item["title"] for item in results]
    assert "Banan" in titles
    assert "Jabłko" in titles
    assert "Mój prywatny posiłek" not in titles


@pytest.mark.django_db
def test_product_with_serving_unit_calculates_correct_values(auth_api_client):
    client, _ = auth_api_client

    product = Product.objects.create(
        title="Oliwa z oliwek",
        kcal_1g=Decimal("8.84000"),
        protein_1g=Decimal("0.00000"),
        fat_1g=Decimal("1.00000"),
        carbohydrates_1g=Decimal("0.00000"),
        user=None,
        package_whole_g=Decimal("500.00"),
        package_name="Butelka 500ml",
    )
    unit = ProductServingUnit.objects.create(
        product=product,
        unit_name="tbsp",
        custom_label="Łyżka stołowa",
        gram_weight=Decimal("10.00"),
    )

    url = "/diet/products/"
    response = client.get(url)
    assert response.status_code == 200

    results = response.data["results"]
    item = next(p for p in results if p["id"] == product.id)

    # Powinna wygrać jednostka serving_unit
    assert item["packaging"] == "Łyżka stołowa"
    assert Decimal(str(item["weight_g"])) == Decimal("10.00")
    # 10g * 8.84 = 88.40 kcal
    assert Decimal(str(item["kcal"])) == Decimal("88.40")
    assert item["serving_unit_id"] == unit.id


@pytest.mark.django_db
def test_product_with_package_whole_g_fallback(auth_api_client):
    client, _ = auth_api_client

    product = Product.objects.create(
        title="Tuńczyk w sosie własnym",
        kcal_1g=Decimal("1.10000"),
        protein_1g=Decimal("0.25000"),
        fat_1g=Decimal("0.01000"),
        carbohydrates_1g=Decimal("0.00000"),
        user=None,
        package_whole_g=Decimal("160.00"),
        package_name="Puszka",
    )

    url = "/diet/products/"
    response = client.get(url)
    assert response.status_code == 200

    results = response.data["results"]
    item = next(p for p in results if p["id"] == product.id)

    assert item["packaging"] == "Puszka"
    assert Decimal(str(item["weight_g"])) == Decimal("160.00")
    # 160g * 1.10 = 176.00 kcal
    assert Decimal(str(item["kcal"])) == Decimal("176.00")
    assert item["serving_unit_id"] is None


@pytest.mark.django_db
def test_product_default_100g_fallback(auth_api_client):
    client, _ = auth_api_client

    product = Product.objects.create(
        title="Ryż Basmati",
        kcal_1g=Decimal("3.50000"),
        protein_1g=Decimal("0.08000"),
        fat_1g=Decimal("0.01000"),
        carbohydrates_1g=Decimal("0.77000"),
        user=None,
        package_whole_g=None,
        package_name=None,
    )

    url = "/diet/products/"
    response = client.get(url)
    assert response.status_code == 200

    results = response.data["results"]
    item = next(p for p in results if p["id"] == product.id)

    assert item["packaging"] == "100g"
    assert Decimal(str(item["weight_g"])) == Decimal("100.00")
    # 100g * 3.50 = 350.00 kcal
    assert Decimal(str(item["kcal"])) == Decimal("350.00")
    assert item["serving_unit_id"] is None


@pytest.mark.django_db
def test_product_list_pagination(auth_api_client):
    client, _ = auth_api_client

    products = [
        Product(
            title=f"Produkt {i:02d}",
            kcal_1g=Decimal("1.00000"),
            protein_1g=Decimal("0.10000"),
            fat_1g=Decimal("0.05000"),
            carbohydrates_1g=Decimal("0.20000"),
            user=None,
        )
        for i in range(25)
    ]
    Product.objects.bulk_create(products)

    url = "/diet/products/"
    response = client.get(url)
    assert response.status_code == 200

    assert response.data["count"] == 25
    assert len(response.data["results"]) == 20
    assert response.data["next"] is not None
    assert response.data["previous"] is None

    # Pobieramy stronę 2
    page2_response = client.get("/diet/products/?page=2")
    assert page2_response.status_code == 200
    assert len(page2_response.data["results"]) == 5
    assert page2_response.data["next"] is None
    assert page2_response.data["previous"] is not None


@pytest.mark.django_db
def test_get_product_by_barcode_happy_path(auth_api_client):
    client, _ = auth_api_client

    product = Product.objects.create(
        title="Baton Proteinowy",
        brand="FitBrand",
        barcode="5901234567890",
        kcal_1g=Decimal("4.00000"),
        protein_1g=Decimal("0.30000"),
        fat_1g=Decimal("0.15000"),
        carbohydrates_1g=Decimal("0.35000"),
        salt_1g=Decimal("0.00500"),
        user=None,
        package_whole_g=Decimal("60.00"),
        package_name="Baton 60g",
    )
    unit = ProductServingUnit.objects.create(
        product=product,
        unit_name="piece",
        custom_label="1 baton",
        gram_weight=Decimal("60.00"),
    )
    from diet.models import ProductAdditionalInfo
    ProductAdditionalInfo.objects.create(
        product=product,
        is_vegan=True,
        is_vegetarian=True,
        ingredients_text="Białko sojowe, czekolada",
    )

    url = f"/diet/products/barcode/{product.barcode}/"
    response = client.get(url)
    assert response.status_code == 200

    data = response.data
    assert data["id"] == product.id
    assert data["title"] == "Baton Proteinowy"
    assert data["brand"] == "FitBrand"
    assert data["barcode"] == "5901234567890"
    assert Decimal(str(data["kcal_100g"])) == Decimal("400.00")
    assert Decimal(str(data["protein_100g"])) == Decimal("30.00")
    assert len(data["serving_units"]) == 1
    assert data["serving_units"][0]["label"] == "1 baton"
    assert data["additional_info"]["is_vegan"] is True
    assert data["additional_info"]["ingredients_text"] == "Białko sojowe, czekolada"


@pytest.mark.django_db
def test_get_product_by_barcode_not_found(auth_api_client):
    client, _ = auth_api_client

    url = "/diet/products/barcode/9999999999999/"
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_product_by_barcode_user_owned_product(auth_api_client):
    client, user = auth_api_client

    product = Product.objects.create(
        title="Własny chleb orkiszowy",
        barcode="5900000000001",
        kcal_1g=Decimal("2.20000"),
        protein_1g=Decimal("0.08000"),
        fat_1g=Decimal("0.02000"),
        carbohydrates_1g=Decimal("0.45000"),
        salt_1g=Decimal("0.01000"),
        user=user,
    )

    url = f"/diet/products/barcode/{product.barcode}/"
    response = client.get(url)
    assert response.status_code == 200
    assert response.data["id"] == product.id
    assert response.data["title"] == "Własny chleb orkiszowy"

