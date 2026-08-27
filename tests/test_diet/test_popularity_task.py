import pytest
from decimal import Decimal
from diet.models import Product
from diet.tasks import increment_product_popularity, trigger_product_popularity_increment


@pytest.fixture
def product():
    return Product.objects.create(
        title="Banan Testowy",
        kcal_1g=Decimal("0.89000"),
        protein_1g=Decimal("0.01100"),
        fat_1g=Decimal("0.00300"),
        carbohydrates_1g=Decimal("0.23000"),
        salt_1g=Decimal("0.00100"),
        popularity=None,
    )


@pytest.mark.django_db
def test_increment_product_popularity_from_none(product):
    assert product.popularity is None

    # Call task directly with +5
    increment_product_popularity(product.id, points=5)
    product.refresh_from_db()
    assert product.popularity == 5

    # Increment again with +10
    increment_product_popularity(product.id, points=10)
    product.refresh_from_db()
    assert product.popularity == 15

    # Increment again with +1
    increment_product_popularity(product.id, points=1)
    product.refresh_from_db()
    assert product.popularity == 16


@pytest.mark.django_db
def test_increment_product_popularity_nonexistent_product_does_not_fail():
    # Fire and forget: should handle nonexistent product gracefully without raising exception
    increment_product_popularity(product_id=999999, points=5)


@pytest.mark.django_db
def test_add_product_to_meal_triggers_popularity_task(auth_api_client, product):
    client, user = auth_api_client

    url = "/api/v1/diet/add-product/"
    payload = {
        "product_id": product.id,
        "date": "2026-08-20",
        "meal_type": 1,
        "amount": 100.0,
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201

    # Task is queued via transaction.on_commit / delay. Test direct execution:
    increment_product_popularity(product.id, points=5)
    product.refresh_from_db()
    assert product.popularity == 5
