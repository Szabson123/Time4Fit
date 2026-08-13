from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce
from user.models import CentralUser
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from typing import List


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
        multiplier = Coalesce(F('amount_g'), Value(0.0), output_field=DecimalField())

        return self.annotate(
            total_kcal=ExpressionWrapper(F('kcal_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_protein=ExpressionWrapper(F('protein_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_fat=ExpressionWrapper(F('fat_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            total_carbohydrates=ExpressionWrapper(F('carbohydrates_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
            display_salt=Case(
                When(label_type='US', then=ExpressionWrapper(
                    (F('salt_1g') / 2.5) * 1000 * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)
                )),
                default=ExpressionWrapper(F('salt_1g') * multiplier, output_field=DecimalField(max_digits=12, decimal_places=2)),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )


class Allergen(models.Model):
    name = models.CharField(max_length=255, db_index=True)



class Product(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey('ProductCategory', on_delete=models.CASCADE, related_name='products')
    
    # Makro na 1g
    kcal_1g = models.DecimalField(max_digits=10, decimal_places=5)
    protein_1g = models.DecimalField(max_digits=10, decimal_places=5)
    fat_1g = models.DecimalField(max_digits=10, decimal_places=5)
    carbohydrates_1g = models.DecimalField(max_digits=10, decimal_places=5)
    salt_1g = models.DecimalField(max_digits=10, decimal_places=5, default=0)

    barcode = models.CharField(max_length=255, db_index=True, blank=True, null=True)
    user = models.ForeignKey('CentralUser', on_delete=models.CASCADE, null=True, blank=True)

    # Informacje o głównym opakowaniu
    package_whole_g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Waga całego opakowania w gramach/ml")
    package_name = models.CharField(max_length=100, null=True, blank=True, help_text="np. Puszka, Kubek, Paczka, Butelka")


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
    created_by = models.ForeignKey('CentralUser', on_delete=models.SET_NULL, null=True, blank=True)
    is_global = models.BooleanField(default=True, help_text="True jeśli miara wygenerowana przez AI/System, False jeśli stworzona przez konkretnego usera")

    def __str__(self):
        label = self.custom_label or self.get_unit_name_display()
        return f"{self.product.title} - {label} ({self.gram_weight}g)"


class Dish(models.Model):
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)

    product = models.ManyToManyField(Product, related_name='dishes', through='DishIngredient')
    category = models.ForeignKey(DishCategory, on_delete=models.SET_NULL, null=True)
    diet_type = models.ForeignKey(DietType, on_delete=models.SET_NULL, null=True, blank=True)

    recipe = models.JSONField(default=dict, null=True, blank=True)
    additional_allergens = models.ManyToManyField(Allergen, related_name='dishes')
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
    calendar = models.ForeignKey(DailyMealCalendar, on_delete=models.CASCADE, related_name='meals')
    name = models.CharField(max_length=100) # np. "Śniadanie", "Przekąska po treningu"
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']


class FullMeal(models.Model):
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, related_name='fullmeal')
    name = models.CharField(max_length=255)
    portion= models.FloatField()



class MealItem(models.Model):
    meal_category = models.ForeignKey(MealCategory, on_delete=models.CASCADE, related_name='items')
    full_meal = models.ForeignKey('FullMeal', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    name = models.CharField(max_length=255)
    
    # Snapshot makro na 1g (zdenormalizowane)
    kcal_1g = models.DecimalField(max_digits=12, decimal_places=5)
    protein_1g = models.DecimalField(max_digits=12, decimal_places=5)
    fat_1g = models.DecimalField(max_digits=12, decimal_places=5)
    carbohydrates_1g = models.DecimalField(max_digits=12, decimal_places=5)
    salt_1g = models.DecimalField(max_digits=12, decimal_places=5, default=0)

    # Wybrana miara i ilość
    product_serving_unit = models.ForeignKey('ProductServingUnit', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=1.0, help_text="Ilość porcji, np. 2 dla 2 plastrów lub 150 dla 150g")
    calculated_gram_weight = models.DecimalField(max_digits=8, decimal_places=2, help_text="Wyliczona końcowa waga w gramach")

    # Referencja historyczna (opcjonalna)
    original_product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    original_recipe = models.ForeignKey('Dish', on_delete=models.SET_NULL, null=True, blank=True)

    objects = MealItemQuerySet.as_manager()
