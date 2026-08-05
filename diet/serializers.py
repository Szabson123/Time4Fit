from rest_framework import serializers
from django.db import transaction

from django.db.models import CharField
from django.contrib.postgres.fields import ArrayField

from .models import Packaging, DishIngredient, ProductCategory, Product, Allergen, Dish
from .services import ProductService


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name']



class DishIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishIngredient
        fields = ['product', 'name_packaging', 'ammount', 'weight_in_g']



class PackagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Packaging
        fields = ['id', 'name', 'default_size', 'default_metric']


class AllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergen
        fields = ['id', 'name']


class ProductCreateSerializer(serializers.ModelSerializer):
    kcal = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    protein = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    fat = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    carbohydrates = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    sodium_salt = serializers.DecimalField(decimal_places=5, max_digits=12, write_only=True)
    allergens = serializers.PrimaryKeyRelatedField(queryset=Allergen.objects.all(), many=True, required=False)

    class Meta:
        model = Product
        fields = ['title', 'label_type', 'category', 'packaging_type', 'packaging_size',
                    'packaging_metric', 'barcode', 'allergens',
                    'kcal', 'protein', 'fat', 'carbohydrates', 'sodium_salt']
        
    def validate(self, attrs):
        instance_label_type = getattr(self.instance, 'label_type', None)
        label_type = attrs.get('label_type', instance_label_type)

        if not label_type:
            raise serializers.ValidationError({"label_type": "Label type is required."})
            
        instance_size = getattr(self.instance, 'packaging_size', None)
        packaging_size = attrs.get('packaging_size', instance_size)

        if label_type == 'US' and not packaging_size:
            raise serializers.ValidationError({
                "packaging_size": "Packaging size is required for US serving-based labels."
            })
            
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        return ProductService.create_product(user, validated_data)

    def update(self, instance, validated_data):
        return ProductService.update_product(instance, validated_data)
    

class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    packaging_type = serializers.CharField(source='packaging_type.name')
    nutrients = serializers.SerializerMethodField()
    allergens = AllergenSerializer(read_only=True, many=True)

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
    

class DishSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.name')
    diet_type = serializers.CharField(source='diet_type.name')

    total_kcal = serializers.DecimalField(decimal_places=5, max_digits=12)
    total_protein = serializers.DecimalField(decimal_places=5, max_digits=12)
    total_fat = serializers.DecimalField(decimal_places=5, max_digits=12)
    total_carbohydrates = serializers.DecimalField(decimal_places=5, max_digits=12)
    display_salt = serializers.DecimalField(decimal_places=5, max_digits=12)

    additional_allergens = AllergenSerializer(read_only=True, many=True)
    products_allergens = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Dish
        fields = ['id', 'name', 'category', 'diet_type',
                  'total_kcal', 'total_protein', 'total_fat', 'total_carbohydrates', 'display_salt',
                  'additional_allergens', 'products_allergens']
        

class RetriveDishSerializer(serializers.ModelSerializer):
    dish_ser = DishSerializer(source="*", many=False, read_only=True)
    ingredients = DishIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Dish
        fields = ['dish_ser', 'recipe', 'img', 'ingredients']


class DishCreateSerializer(serializers.ModelSerializer):
    ingredients = DishIngredientSerializer(many=True)
    additional_allergens = serializers.PrimaryKeyRelatedField(many=True, queryset=Allergen.objects.all(), required=False)

    class Meta:
        model = Dish
        fields = ['name', 'category', 'diet_type', 'recipe', 'ingredients', 'additional_allergens']

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        allergens_data = validated_data.pop('additional_allergens', [])

        dish = Dish.objects.create(**validated_data)

        dish.additional_allergens.set(allergens_data)
        
        for ingredient_data in ingredients_data:
            DishIngredient.objects.create(dish=dish, **ingredient_data)

        return dish
    
    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        allergens_data = validated_data.pop('additional_allergens', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if allergens_data is not None:
            instance.additional_allergens.set(allergens_data)

        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ingredient_data in ingredients_data:
                DishIngredient.objects.create(dish=instance, **ingredient_data)

        return instance
