from django.db import models
from user.models import CentralUser


class ProductCategory(models.Model):
    name = models.CharField(max_length=255)


class Packaging(models.Model):
    name = models.CharField(max_length=255)
    default_size = models.CharField()
    default_metric = models.CharField()


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
    fiber_1g = models.DecimalField(max_digits=12, decimal_places=5, default=0) # Ważne dla USA

    packaging_type = models.ForeignKey(Packaging, on_delete=models.CASCADE) #US/EU
    packaging_size = models.DecimalField(max_digits=8, decimal_places=2, default=100.00) #US -> required EU -> Not requred
    packaging_metric = models.CharField(max_length=10) #US/EU # 'g', 'ml', 'oz'

    barcode = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(upload_to='products_images/', blank=True, null=True)
    

class Allergen(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='allergens')

