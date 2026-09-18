from django.contrib import admin
from .models import ProductDescription, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['title', 'barcode']


@admin.register(ProductDescription)
class ProductDescriptionAdmin(admin.ModelAdmin):
    autocomplete_fields = ['product']
