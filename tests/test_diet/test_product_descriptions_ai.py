import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest

from diet.models import Product, ProductDescription, ProductCategory, ProductAdditionalInfo
from diet.tasks import generate_product_descriptions, trigger_generate_product_descriptions


@pytest.fixture
def sample_product():
    cat = ProductCategory.objects.create(name="Nabiał")
    prod = Product.objects.create(
        title="Jogurt Naturalny Bio",
        brand="Mleczna Dolina",
        barcode="5900000000001",
        category=cat,
        kcal_1g=Decimal("0.60000"),
        protein_1g=Decimal("0.04000"),
        fat_1g=Decimal("0.03000"),
        carbohydrates_1g=Decimal("0.05000"),
        salt_1g=Decimal("0.00100"),
        sugars_1g=Decimal("0.05000"),
        saturated_fat_1g=Decimal("0.02000"),
        fiber_1g=Decimal("0.00000"),
        nutriscore="A",
        nova_group=1,
        allergens=["milk"],
    )
    ProductAdditionalInfo.objects.create(
        product=prod,
        is_vegetarian=True,
        ingredients_text="mleko pasteryzowane, żywe kultury bakterii jogurtowych",
        labels=["bio", "organic"],
    )
    return prod


@pytest.fixture
def mock_openrouter_payload():
    return {
        "en": [f"English fact {i} about natural yogurt." for i in range(1, 6)],
        "de": [f"Deutsche Tatsache {i} über Naturjoghurt." for i in range(1, 6)],
        "pl": [f"Polska ciekawostka {i} o jogurcie naturalnym." for i in range(1, 6)],
        "it": [f"Curiosità italiana {i} sullo yogurt naturale." for i in range(1, 6)],
        "es": [f"Dato curioso en español {i} sobre el yogur natural." for i in range(1, 6)],
        "fr": [f"Fait intéressant en français {i} sur le yaourt nature." for i in range(1, 6)],
    }


@pytest.mark.django_db
def test_generate_product_descriptions_creates_30_descriptions(sample_product, mock_openrouter_payload):
    # Ensure no descriptions at first
    assert ProductDescription.objects.filter(product=sample_product).count() == 0

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(mock_openrouter_payload)
                }
            }
        ]
    }

    with patch("diet.tasks.requests.post", return_value=mock_response) as mock_post, \
         patch("django.conf.settings.OPENROUTER_API_KEY", "test-api-key"):
        generate_product_descriptions(sample_product.id)

        assert mock_post.called
        assert ProductDescription.objects.filter(product=sample_product).count() == 30

        # Check each language has exactly 5 descriptions
        for lang in ['en', 'de', 'pl', 'it', 'es', 'fr']:
            count = ProductDescription.objects.filter(product=sample_product, language=lang).count()
            assert count == 5


@pytest.mark.django_db
def test_generate_product_descriptions_skips_if_already_exist(sample_product, mock_openrouter_payload):
    ProductDescription.objects.create(
        product=sample_product,
        language="pl",
        description="Istniejący opis."
    )

    with patch("diet.tasks.requests.post") as mock_post:
        generate_product_descriptions(sample_product.id)
        mock_post.assert_not_called()

    assert ProductDescription.objects.filter(product=sample_product).count() == 1


@pytest.mark.django_db
def test_product_detail_by_id_triggers_task_when_no_descriptions(auth_api_client, sample_product):
    client, user = auth_api_client

    with patch("diet.views.trigger_generate_product_descriptions") as mock_trigger:
        response = client.get(f"/api/v1/diet/products/{sample_product.id}/")
        assert response.status_code == 200
        mock_trigger.assert_called_once_with(sample_product.id)


@pytest.mark.django_db
def test_product_detail_by_id_does_not_trigger_task_when_descriptions_exist(auth_api_client, sample_product):
    client, user = auth_api_client
    ProductDescription.objects.create(
        product=sample_product,
        language="pl",
        description="Już istnieje."
    )

    with patch("diet.views.trigger_generate_product_descriptions") as mock_trigger:
        response = client.get(f"/api/v1/diet/products/{sample_product.id}/")
        assert response.status_code == 200
        mock_trigger.assert_not_called()


@pytest.mark.django_db
def test_product_detail_by_barcode_triggers_task_when_no_descriptions(auth_api_client, sample_product):
    client, user = auth_api_client

    with patch("diet.views.trigger_generate_product_descriptions") as mock_trigger:
        response = client.get(f"/api/v1/diet/products/barcode/{sample_product.barcode}/")
        assert response.status_code == 200
        mock_trigger.assert_called_once_with(sample_product.id)


@pytest.mark.django_db
def test_product_detail_by_barcode_does_not_trigger_task_when_descriptions_exist(auth_api_client, sample_product):
    client, user = auth_api_client
    ProductDescription.objects.create(
        product=sample_product,
        language="pl",
        description="Już istnieje."
    )

    with patch("diet.views.trigger_generate_product_descriptions") as mock_trigger:
        response = client.get(f"/api/v1/diet/products/barcode/{sample_product.barcode}/")
        assert response.status_code == 200
        mock_trigger.assert_not_called()


@pytest.mark.django_db
def test_product_detail_random_description_according_to_user_profile_language(auth_api_client, sample_product):
    client, user = auth_api_client

    # Set user profile language to German ('de')
    if hasattr(user, 'profile'):
        user.profile.language = 'de'
        user.profile.save()

    # Create 5 German descriptions and 5 Polish descriptions
    de_facts = [f"Deutsche Tatsache {i}" for i in range(1, 6)]
    pl_facts = [f"Polska ciekawostka {i}" for i in range(1, 6)]

    for desc in de_facts:
        ProductDescription.objects.create(product=sample_product, language='de', description=desc)
    for desc in pl_facts:
        ProductDescription.objects.create(product=sample_product, language='pl', description=desc)

    # Calling product detail without query param should return a German description
    response = client.get(f"/api/v1/diet/products/{sample_product.id}/")
    assert response.status_code == 200
    assert response.data["product_desc"] in de_facts

    # Calling with query param ?lang=pl should return a Polish description
    response_pl = client.get(f"/api/v1/diet/products/{sample_product.id}/?lang=pl")
    assert response_pl.status_code == 200
    assert response_pl.data["product_desc"] in pl_facts
