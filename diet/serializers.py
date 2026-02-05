from rest_framework import serializers

from .models import Packaging, ProductCategory, Product


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name']


class Packaging(serializers.ModelSerializer):
    class Meta:
        model = Packaging
        fields = ['id', 'name', 'default_size', 'default_metric']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'label_type', 'title', 'packaging_size', 'packaging_metric'
                  'barcode', 'image']