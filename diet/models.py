from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField, Case, When, Value, Q
from django.db.models.functions import Coalesce
from user.models import CentralUser
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from typing import List
from django.contrib.postgres.indexes import GinIndex

class ProductCountry(models.Model):
    name = models.CharField(max_length=255)


class ProductCategory(models.Model):
    name = models.CharField(max_length=255)


class DishCategory(models.Model):
    name = models.CharField(max_length=255)


class DietType(models.Model):
    name = models.CharField(max_length=255)


class Packaging(models.Model):
    name = models.CharField(max_length=255)
    default_size = models.CharField()
    default_metric = models.CharField()


class ProductQuerySet(models.QuerySet):
    def with_nutrients(self):
        multiplier = Coalesce(F('packaging_size'), Value(100.0))

        return self.annotate(
            total_kcal = ExpressionWrapper(F('kcal_1g') * multiplier, output_field=DecimalField()),
            total_protein = ExpressionWrapper(F('protein_1g') * multiplier, output_field=DecimalField()),
            total_fat = ExpressionWrapper(F('fat_1g') * multiplier, output_field=DecimalField()),
            total_carbohydrates = ExpressionWrapper(F('carbohydrates_1g') * multiplier, output_field=DecimalField()),
            display_salt=Case(
                When(label_type='US', then=ExpressionWrapper(
                    (F('salt_1g') / 2.5) * 1000 * multiplier, output_field=DecimalField()
                )),
                default=ExpressionWrapper(F('salt_1g') * multiplier, output_field=DecimalField()),
                output_field=DecimalField()
            )
        )
    
    def with_allergens(self):
        return self.prefetch_related('allergens')


class MealItemQuerySet(models.QuerySet):
    def with_nutrients(self):
        multiplier = Coalesce(F('calculated_gram_weight'), Value(0.0), output_field=DecimalField())

        return self.annotate(
            total_kcal=ExpressionWrapper(F('kcal_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_protein=ExpressionWrapper(F('protein_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_fat=ExpressionWrapper(F('fat_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_carbohydrates=ExpressionWrapper(F('carbohydrates_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            display_salt=ExpressionWrapper(F('salt_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
        )


class Product(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    brand = models.CharField(max_length=150,blank=True,null=True,db_index=True,help_text="np. Piątnica, Bovetti")
    barcode = models.CharField(max_length=64, db_index=True, blank=True, null=True, help_text="EAN-13, EAN-8, UPC")
    quantity_display = models.CharField(max_length=100, blank=True, null=True, help_text="Oryginalny tekst z etykiety np. '350 g', '4 x 125g'",)

    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Link do miniatury z CDN",)
    
    category = models.ForeignKey('ProductCategory', related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey('user.CentralUser', on_delete=models.CASCADE, null=True, blank=True)

    # Makro na 1g
    kcal_1g = models.DecimalField(max_digits=10, decimal_places=5)
    protein_1g = models.DecimalField(max_digits=10, decimal_places=5)
    fat_1g = models.DecimalField(max_digits=10, decimal_places=5)
    carbohydrates_1g = models.DecimalField(max_digits=10, decimal_places=5)
    salt_1g = models.DecimalField(max_digits=10, decimal_places=5, default=0)

    sugars_1g = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    saturated_fat_1g = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    fiber_1g = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)

    nutriscore = models.CharField(max_length=1, choices=[("A", "A"),("B", "B"),("C", "C"),("D", "D"),("E", "E")], null=True, blank=True, db_index=True)
    nova_group = models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4")], null=True, blank=True, db_index=True)
    
    allergens = models.JSONField(default=list, blank=True, help_text="np. ['milk', 'nuts']")
    countries = models.JSONField(default=list, blank=True, help_text="Kraje dystrybucji: ['poland', 'germany']",)

    # Informacje o głównym opakowaniu
    package_whole_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Waga całego opakowania w gramach/ml")
    package_name = models.CharField(max_length=100, null=True, blank=True, help_text="np. Puszka, Kubek, Paczka, Butelka")

    popularity = models.IntegerField(null=True, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["barcode"]),
            models.Index(fields=["-popularity", "-id"], name="product_pop_id_idx"),
            GinIndex(
                name='product_title_trgm_gin_idx',
                fields=['title'],
                opclasses=['gin_trgm_ops'],
                condition=Q(user__isnull=True),
            ),
        ]

    def __str__(self):
        brand_prefix = f"[{self.brand}] " if self.brand else ""
        return f"{brand_prefix}{self.title}"


class ProductAdditionalInfo(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="additional_info", primary_key=True)
    is_vegan = models.BooleanField(null=True, blank=True, db_index=True)
    is_vegetarian = models.BooleanField(null=True, blank=True, db_index=True)
    is_palm_oil_free = models.BooleanField(null=True, blank=True)
    is_complete_profile = models.BooleanField(default=True, help_text="True jeśli produkt ma kompletne dane o cukrach i tłuszczach nasyconych",)
    ingredients_text = models.TextField(blank=True, null=True)
    traces = models.JSONField(default=list, blank=True, help_text="Śladowe ilości: ['soybeans', 'gluten']",)
    labels = models.JSONField(default=list, blank=True, help_text="Certyfikaty: ['bio', 'no-gluten', 'organic']",)
    additives_tags = models.JSONField(default=list, blank=True, help_text="Lista dodatków E: ['e322', 'e330']")


class ProductDescription(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='descriptions')
    language = models.CharField(max_length=10, default='pl', db_index=True)
    description = models.TextField()

    class Meta:
        unique_together = ('product', 'language')

    def __str__(self):
        return f"{self.product.title} [{self.language}]"


class ProductServingUnit(models.Model):
    UNIT_CHOICES = [
        ('g', 'Gram'),
        ('ml', 'Mililitr'),
        ('piece', 'Sztuka'),
        ('slice', 'Plaster'),
        ('cup', 'Szklanka / Kubek'),
        ('tbsp', 'Łyżka'),
        ('tsp', 'Łyżeczka'),
        ('can', 'Puszka'),
        ('pack', 'Opakowanie / Paczka'),
        ('handful', 'Garść'),
        ('serving', 'Porcja producenta'),
        ('custom', 'Własna miara'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serving_units')
    unit_name = models.CharField(max_length=20, choices=UNIT_CHOICES)
    custom_label = models.CharField(max_length=100, blank=True, null=True, help_text="np. Duża łyżka, Szklanka 250ml")
    
    gram_weight = models.DecimalField(max_digits=8, decimal_places=2)

    # DODATKOWE POLA DLA DANYCH OD UŻYTKOWNIKA / AI
    created_by = models.ForeignKey('user.CentralUser', on_delete=models.SET_NULL, null=True, blank=True)
    is_global = models.BooleanField(default=True, help_text="True jeśli miara wygenerowana przez AI/System, False jeśli stworzona przez konkretnego usera")

    class Meta:
        indexes = [
            models.Index(fields=['product', 'id']),
        ]

    def __str__(self):
        label = self.custom_label or self.get_unit_name_display()
        return f"{self.product.title} - {label} ({self.gram_weight}g)"


class Dish(models.Model):
    user = models.ForeignKey('user.CentralUser', on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)

    product = models.ManyToManyField(Product, related_name='dishes', through='DishIngredient')
    category = models.ForeignKey(DishCategory, on_delete=models.SET_NULL, null=True)
    diet_type = models.ForeignKey(DietType, on_delete=models.SET_NULL, null=True, blank=True)

    recipe = models.JSONField(default=dict, null=True, blank=True)
    img = models.ImageField(upload_to='dishes_images/', blank=True, null=True)


class DishIngredient(models.Model):
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='ingredients')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    name_packaging = models.CharField(default=None, null=True, blank=True)
    ammount = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    weight_in_g = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def clean(self):
        super().clean()
        if self.name_packaging:
            if not Packaging.objects.filter(name=self.name_packaging).exists():
                raise ValidationError({
                    'error': f"Opakowanie '{self.name_packaging}' nie istnieje w bazie systemowej.", "code": 'packaging doesnt exist'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DailyMealCalendar(models.Model):
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    date = models.DateField()

    class Meta:
        unique_together = ('user', 'date')


class MealCategory(models.Model):
    MEAL_TYPE_CHOICES = [
        (1, 'Śniadanie'),
        (2, 'Drugie śniadanie'),
        (3, 'Obiad'),
        (4, 'Podwieczorek'),
        (5, 'Kolacja'),
        (6, 'Custom'),
    ]

    calendar = models.ForeignKey(DailyMealCalendar, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.PositiveSmallIntegerField(choices=MEAL_TYPE_CHOICES, default=1)
    name = models.CharField(max_length=100, blank=True, null=True) # np. "Śniadanie", "Przekąska po treningu"
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.name and self.meal_type and self.meal_type > 5:
            self.name = f"Posiłek {self.meal_type}"
        super().save(*args, **kwargs)


class FullMeal(models.Model):
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, related_name='fullmeal')
    name = models.CharField(max_length=255)
    portion= models.FloatField()


class MealItem(models.Model):
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, related_name='items')
    full_meal = models.ForeignKey('FullMeal', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    name = models.CharField(max_length=255)
    
    kcal_1g = models.DecimalField(max_digits=12, decimal_places=5)
    protein_1g = models.DecimalField(max_digits=12, decimal_places=5)
    fat_1g = models.DecimalField(max_digits=12, decimal_places=5)
    carbohydrates_1g = models.DecimalField(max_digits=12, decimal_places=5)
    salt_1g = models.DecimalField(max_digits=12, decimal_places=5, default=0)

    product_serving_unit = models.ForeignKey('ProductServingUnit', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=1.0, help_text="Ilość porcji, np. 2 dla 2 plastrów lub 150 dla 150g")
    calculated_gram_weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Wyliczona końcowa waga w gramach")

    original_product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    original_recipe = models.ForeignKey('Dish', on_delete=models.SET_NULL, null=True, blank=True)

    objects = MealItemQuerySet.as_manager()
