from django.contrib import admin
from .models import ProductDescription


@admin.register(ProductDescription)
class ProductDescriptionAdmin(admin.ModelAdmin):
    autocomplete_fields = ['product']
