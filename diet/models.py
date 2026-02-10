from django.db import models
from django.db.models import F, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce
from user.models import CentralUser
from decimal import Decimal, ROUND_HALF_UP


class ProductCountry(models.Model):
    name = models.CharField(max_length=255)


class ProductCategory(models.Model):
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


class Product(models.Model):
    LABEL_CHOICES = [('EU', 'Europe'), ('US', 'USA')]
    label_type = models.CharField(max_length=2, choices=LABEL_CHOICES)
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')

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

    objects = ProductQuerySet.as_manager()


class Allergen(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    product = models.ManyToManyField(Product, related_name='allergens')

