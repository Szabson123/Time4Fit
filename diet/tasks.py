import json
import logging
import os
import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)


@shared_task(name="diet.tasks.increment_product_popularity", ignore_result=True)
def increment_product_popularity(product_id: int, points: int = 5):
    """
    Asynchroniczne zadanie (fire-and-forget) zwiększające popularność produktu
    o zadaną liczbę punktów (np. 1, 5, 10).
    """
    try:
        from .models import Product
        Product.objects.filter(id=product_id).update(
            popularity=Coalesce(F('popularity'), 0) + points
        )
    except Exception as e:
        logger.error(f"Błąd podczas zwiększania popularności produktu (id={product_id}): {e}")


def trigger_product_popularity_increment(product_id: int, points: int = 5):
    """
    Pomocnicza funkcja fire-and-forget do asynchronicznego uruchamiania taska Celery.
    Nie blokuje głównego wątku ani nie rzuca wyjątków w przypadku awarii brokera/kolejki.
    """
    try:
        transaction.on_commit(lambda: increment_product_popularity.delay(product_id, points))
    except Exception as e:
        logger.warning(f"Nie udało się zakolejkować zwiększenia popularności produktu {product_id}: {e}")


@shared_task(name="diet.tasks.generate_product_descriptions", ignore_result=True)
def generate_product_descriptions(product_id: int):
    """
    Asynchroniczne zadanie (fire-and-forget) odpytujące OpenRouter o wygenerowanie
    ciekawostek (5 per język dla: en, de, pl, it, es, fr) i zapisujące je w ProductDescription.
    """
    from .models import Product, ProductDescription

    # Jeśli produkt ma już opisy, nic nie robimy
    if ProductDescription.objects.filter(product_id=product_id).exists():
        return

    lock_key = f"generate_desc_lock_{product_id}"
    if not cache.add(lock_key, True, timeout=180):
        return

    try:
        if ProductDescription.objects.filter(product_id=product_id).exists():
            return

        product = (
            Product.objects
            .select_related('additional_info', 'category')
            .filter(id=product_id)
            .first()
        )
        if not product:
            return

        api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        if not api_key:
            logger.warning(f"Brak OPENROUTER_API_KEY. Pomijanie generowania opisów dla produktu {product_id}.")
            return

        model = getattr(settings, 'OPENROUTER_MODEL', 'google/gemini-2.0-flash-001')
        base_url = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

        prompt_file = os.path.join(settings.BASE_DIR, 'diet', 'prompts', 'product_descriptions.txt')
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()

        additional = getattr(product, 'additional_info', None)
        ingredients = additional.ingredients_text if additional and additional.ingredients_text else 'N/A'
        labels = ", ".join(additional.labels) if additional and additional.labels else 'brak'

        prompt_content = template.format(
            title=product.title,
            brand=product.brand or 'N/A',
            category=product.category.name if product.category else 'N/A',
            ingredients=ingredients,
            nutriscore=product.nutriscore or 'N/A',
            nova_group=product.nova_group or 'N/A',
            allergens=", ".join(product.allergens) if product.allergens else 'brak',
            labels=labels,
            energy_kcal=round(float(product.kcal_1g) * 100, 1),
            protein_g=round(float(product.protein_1g) * 100, 1),
            carbs_g=round(float(product.carbohydrates_1g) * 100, 1),
            sugars_g=round(float(product.sugars_1g) * 100, 1) if product.sugars_1g is not None else 'N/A',
            fat_g=round(float(product.fat_1g) * 100, 1),
            sat_fat_g=round(float(product.saturated_fat_1g) * 100, 1) if product.saturated_fat_1g is not None else 'N/A',
            fiber_g=round(float(product.fiber_1g) * 100, 1) if product.fiber_1g is not None else 'N/A',
            salt_g=round(float(product.salt_1g) * 100, 2),
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Time4Fit",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional nutrition expert and food science writer. Output strictly valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt_content
                }
            ],
            "response_format": {"type": "json_object"}
        }

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=45
        )
        response.raise_for_status()

        result_data = response.json()
        raw_text = result_data["choices"][0]["message"]["content"].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed = json.loads(raw_text.strip())

        supported_languages = ['en', 'de', 'pl', 'it', 'es', 'fr']
        new_objects = []
        for lang in supported_languages:
            items = parsed.get(lang, [])
            if isinstance(items, list):
                for fact in items[:5]:
                    text = str(fact).strip()
                    if text:
                        new_objects.append(
                            ProductDescription(
                                product_id=product_id,
                                language=lang,
                                description=text
                            )
                        )

        if new_objects:
            ProductDescription.objects.bulk_create(new_objects)
            logger.info(f"Utworzono {len(new_objects)} opisów dla produktu {product_id}.")

    except Exception as e:
        logger.error(f"Błąd podczas generowania opisów przez OpenRouter dla produktu {product_id}: {e}")
    finally:
        cache.delete(lock_key)


def trigger_generate_product_descriptions(product_id: int):
    """
    Pomocnicza funkcja fire-and-forget do asynchronicznego uruchamiania generowania opisów.
    Sprawdza, czy opisy istnieją – jeśli nie, zleca zadanie w tle po zatwierdzeniu transakcji.
    """
    try:
        from .models import ProductDescription
        if ProductDescription.objects.filter(product_id=product_id).exists():
            return

        def _dispatch():
            try:
                generate_product_descriptions.delay(product_id)
            except Exception as e:
                logger.warning(f"Nie udało się zakolejkować zadania generowania opisów dla produktu {product_id}: {e}")

        transaction.on_commit(_dispatch)
    except Exception as e:
        logger.warning(f"Błąd przy przygotowaniu zadania generowania opisów dla produktu {product_id}: {e}")

