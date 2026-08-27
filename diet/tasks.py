import logging
from celery import shared_task
from django.db.models import F
from django.db.models.functions import Coalesce
from django.db import transaction

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
