from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce
from user.models import CentralUser
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError

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


class Allergen(models.Model):
    name = models.CharField(max_length=255, db_index=True)


class Product(models.Model):
    LABEL_CHOICES = [('EU', 'Europe'), ('US', 'USA')]
    label_type = models.CharField(max_length=2, choices=LABEL_CHOICES)
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    allergens = models.ManyToManyField(Allergen, related_name='products')

    # In USA we put kcal per serving in EU per 100g then endpoint/service make logic 
    kcal_1g = models.DecimalField(max_digits=12, decimal_places=5)
    protein_1g = models.DecimalField(max_digits=12, decimal_places=5)
    fat_1g = models.DecimalField(max_digits=12, decimal_places=5)
    carbohydrates_1g = models.DecimalField(max_digits=12, decimal_places=5)
    salt_1g = models.DecimalField(max_digits=12, decimal_places=5, default=0)

    packaging_type = models.ForeignKey(Packaging, on_delete=models.CASCADE) #US/EU
    packaging_size = models.DecimalField(max_digits=8, decimal_places=2, default=100.00) #US -> required EU -> Not requred
    packaging_metric = models.CharField(max_length=10) #US/EU # 'g', 'ml', 'oz'

    barcode = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(upload_to='products_images/', blank=True, null=True)
    countries = models.ManyToManyField(ProductCountry, related_name='products')

    objects = ProductQuerySet.as_manager()


class Dish(models.Model):
    author = models.ForeignKey(CentralUser, on_delete=models.CASCADE, null=True, blank=True)
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