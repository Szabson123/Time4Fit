from rest_framework import serializers

from .models import Packaging, ProductCategory, Product, Allergen
from .services import ProductService


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name']


class PackagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Packaging
        fields = ['id', 'name', 'default_size', 'default_metric']


class AllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergen
        fields = ['name']


class ProductCreateSerializer(serializers.ModelSerializer):
    kcal = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    protein = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    fat = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    carbohydrates = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    sodium_salt = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    allergen_names = serializers.ListField(
        child=serializers.CharField(), 
        required=False, 
        write_only=True
    )

    class Meta:
        model = Product
        fields = ['title', 'label_type', 'category', 'packaging_type', 'packaging_size',
                    'packaging_metric', 'barcode', 'allergen_names',
                    'kcal', 'protein', 'fat', 'carbohydrates', 'sodium_salt']
        
    def validate(self, attrs):
        label_type = attrs.get('label_type')
        if not label_type:
            raise serializers.ValidationError({"label_type": "Label type is required."})
            
        if label_type == 'US' and not attrs.get('packaging_size'):
            raise serializers.ValidationError({"packaging_size": "Packaging size is required for US serving-based labels."})
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        allergens_data = validated_data.pop("allergens", [])

        product = ProductService.create_product(user, validated_data)

        """
            if allergens_data:
                allergen_instances = []

                for name in allergens_data:
                    new_allergen = Allergen(product=product, name=name)
                    allergen_instances.append(new_allergen)

            Allergen.objects.bulk_create(allergen_instances)
        """

        if allergens_data:
            allergen_instances = [Allergen(product=product, name=name) for name in allergens_data]
            Allergen.objects.bulk_create(allergen_instances)

        return product
    

class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    packaging_type = serializers.CharField(source='packaging_type.name')
    nutrients = serializers.SerializerMethodField()
    allergens = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'label_type', 'category', 'packaging_type', 
            'packaging_size', 'packaging_metric', 'barcode', 
            'allergens', 'nutrients'
        ]

    def get_nutrients(self, obj):
        return {
            'kcal': round(getattr(obj, 'total_kcal', 0)),
            'protein': round(getattr(obj, 'total_protein', 0), 1),
            'fat': round(getattr(obj, 'total_fat', 0), 1),
            'carbohydrates': round(getattr(obj, 'total_carbs', 0), 1),
            'sodium_salt': round(getattr(obj, 'display_salt', 0), 2),
        }