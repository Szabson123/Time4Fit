import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from diet.models import (
    Product,
    ProductAdditionalInfo,
    ProductCategory,
    ProductServingUnit,
)


def to_dec(val, div=1):
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val)) / Decimal(str(div))
    except Exception:
        return None


def clean_text(val):
    if isinstance(val, str):
        return val.replace("\x00", "").strip()
    return val


def clean_data(val):
    if isinstance(val, str):
        return val.replace("\x00", "")
    elif isinstance(val, list):
        return [clean_data(item) for item in val]
    elif isinstance(val, dict):
        return {k: clean_data(v) for k, v in val.items()}
    return val


class Command(BaseCommand):
    help = "Prosty import produktów z pliku jsonl z sanityzacją znaków NUL"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)
        parser.add_argument(
            "--skip",
            type=int,
            default=0,
            help="Liczba linii do pominięcia (jeśli import wywalił się w trakcie)",
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        skip_lines = options["skip"]
        batch_size = 5000

        products_batch = []
        raw_rows = []
        count = skip_lines
        line_num = 0

        if skip_lines > 0:
            self.stdout.write(self.style.WARNING(f"Pomijam pierwsze {skip_lines:,} linii..."))

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_num += 1
                if line_num <= skip_lines:
                    continue

                if not line.strip():
                    continue

                try:
                    row = json.loads(line)
                except Exception:
                    continue

                nutri = row.get("nutriments_100g") or {}

                category = None
                raw_category = clean_text(row.get("category"))
                if raw_category:
                    category, _ = ProductCategory.objects.get_or_create(
                        name=raw_category
                    )

                p = Product(
                    title=clean_text(row.get("name")) or "Bez nazwy",
                    brand=clean_text(row.get("brand")),
                    barcode=clean_text(str(row.get("id"))) if row.get("id") else None,
                    quantity_display=clean_text(row.get("quantity")),
                    image_url=clean_text(row.get("image_url")),
                    category=category,
                    kcal_1g=to_dec(nutri.get("energy_kcal"), 100) or Decimal(0),
                    protein_1g=to_dec(nutri.get("proteins"), 100) or Decimal(0),
                    fat_1g=to_dec(nutri.get("fat"), 100) or Decimal(0),
                    carbohydrates_1g=to_dec(nutri.get("carbohydrates"), 100) or Decimal(0),
                    salt_1g=to_dec(nutri.get("salt"), 100) or Decimal(0),
                    sugars_1g=to_dec(nutri.get("sugars"), 100),
                    saturated_fat_1g=to_dec(nutri.get("saturated_fat"), 100),
                    fiber_1g=to_dec(nutri.get("fiber"), 100),
                    nutriscore=clean_text(row.get("nutriscore")),
                    nova_group=row.get("nova_group"),
                    allergens=clean_data(row.get("allergens") or []),
                    countries=clean_data(row.get("countries") or []),
                    package_whole_g=to_dec(row.get("package_whole_g")),
                    package_name=clean_text(row.get("package_name")),
                )

                products_batch.append(p)
                raw_rows.append(row)

                if len(products_batch) >= batch_size:
                    self.save_batch(products_batch, raw_rows)
                    count += len(products_batch)
                    self.stdout.write(f"Zaimportowano łącznie: {count:,} produktów...")
                    products_batch = []
                    raw_rows = []

            if products_batch:
                self.save_batch(products_batch, raw_rows)
                count += len(products_batch)

        self.stdout.write(self.style.SUCCESS(f"Gotowe! Łącznie przetworzono: {count:,}"))

    def save_batch(self, products, raw_rows):
        with transaction.atomic():
            created_prods = Product.objects.bulk_create(products)

            infos = []
            servings = []

            for prod, raw in zip(created_prods, raw_rows):
                diet = raw.get("diet_flags") or {}
                additives = raw.get("additives") or {}

                infos.append(
                    ProductAdditionalInfo(
                        product=prod,
                        is_vegan=diet.get("is_vegan"),
                        is_vegetarian=diet.get("is_vegetarian"),
                        is_palm_oil_free=diet.get("is_palm_oil_free"),
                        is_complete_profile=raw.get("is_complete_profile", True),
                        ingredients_text=clean_text(raw.get("ingredients")),
                        traces=clean_data(raw.get("traces") or []),
                        labels=clean_data(raw.get("labels") or []),
                        additives_tags=clean_data(additives.get("tags") or []),
                    )
                )

                serving_g = to_dec(raw.get("serving_g"))
                if serving_g:
                    servings.append(
                        ProductServingUnit(
                            product=prod,
                            unit_name="serving",
                            custom_label="Porcja producenta",
                            gram_weight=serving_g,
                            is_global=True,
                        )
                    )

            ProductAdditionalInfo.objects.bulk_create(infos)
            if servings:
                ProductServingUnit.objects.bulk_create(servings)