from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from django.db.models import CharField, Q
from django.contrib.postgres.fields import ArrayField

from .models import (
    MealItem, MealCategory, FullMeal, DailyMealCalendar,
    ProductServingUnit, Product, ProductAdditionalInfo
)


class ProductAdditionalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAdditionalInfo
        fields = [
            'is_vegan',
            'is_vegetarian',
            'is_palm_oil_free',
            'is_complete_profile',
            'ingredients_text',
            'traces',
            'labels',
            'additives_tags',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    serving_units = serializers.SerializerMethodField()
    additional_info = ProductAdditionalInfoSerializer(read_only=True)

    kcal_100g = serializers.SerializerMethodField()
    protein_100g = serializers.SerializerMethodField()
    fat_100g = serializers.SerializerMethodField()
    carbohydrates_100g = serializers.SerializerMethodField()
    salt_100g = serializers.SerializerMethodField()
    sugars_100g = serializers.SerializerMethodField()
    saturated_fat_100g = serializers.SerializerMethodField()
    fiber_100g = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'title',
            'brand',
            'barcode',
            'image_url',
            'quantity_display',
            'category',
            'category_name',
            'package_name',
            'package_whole_g',
            'nutriscore',
            'nova_group',
            'allergens',
            'countries',
            'kcal_1g',
            'protein_1g',
            'fat_1g',
            'carbohydrates_1g',
            'salt_1g',
            'sugars_1g',
            'saturated_fat_1g',
            'fiber_1g',
            'kcal_100g',
            'protein_100g',
            'fat_100g',
            'carbohydrates_100g',
            'salt_100g',
            'sugars_100g',
            'saturated_fat_100g',
            'fiber_100g',
            'serving_units',
            'additional_info',
        ]

    def get_serving_units(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        filter_q = Q(is_global=True)
        if user:
            filter_q |= Q(created_by=user)
        return ProductServingUnitSerializer(obj.serving_units.filter(filter_q), many=True).data

    def get_kcal_100g(self, obj):
        return round(obj.kcal_1g * 100, 2) if obj.kcal_1g is not None else None

    def get_protein_100g(self, obj):
        return round(obj.protein_1g * 100, 2) if obj.protein_1g is not None else None

    def get_fat_100g(self, obj):
        return round(obj.fat_1g * 100, 2) if obj.fat_1g is not None else None

    def get_carbohydrates_100g(self, obj):
        return round(obj.carbohydrates_1g * 100, 2) if obj.carbohydrates_1g is not None else None

    def get_salt_100g(self, obj):
        return round(obj.salt_1g * 100, 2) if obj.salt_1g is not None else None

    def get_sugars_100g(self, obj):
        return round(obj.sugars_1g * 100, 2) if obj.sugars_1g is not None else None

    def get_saturated_fat_100g(self, obj):
        return round(obj.saturated_fat_1g * 100, 2) if obj.saturated_fat_1g is not None else None

    def get_fiber_100g(self, obj):
        return round(obj.fiber_1g * 100, 2) if obj.fiber_1g is not None else None



class ProductListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    packaging = serializers.SerializerMethodField()
    weight_g = serializers.SerializerMethodField()
    kcal = serializers.SerializerMethodField()
    serving_unit_id = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'title',
            'brand',
            'image_url',
            'packaging',
            'weight_g',
            'kcal',
            'kcal_1g',
            'serving_unit_id',
        ]

    def _get_first_serving(self, obj):
        servings = getattr(obj, 'prefetched_servings', [])
        return servings[0] if servings else None

    def _get_weight(self, obj):
        unit = self._get_first_serving(obj)
        if unit and unit.gram_weight is not None:
            return unit.gram_weight
        if obj.package_whole_g is not None:
            return obj.package_whole_g
        return Decimal('100.00')

    def get_packaging(self, obj):
        unit = self._get_first_serving(obj)
        if unit:
            return unit.custom_label or unit.get_unit_name_display()
        if obj.package_name:
            return obj.package_name
        return "100g"

    def get_weight_g(self, obj):
        weight = self._get_weight(obj)
        return f"{Decimal(weight):.2f}"

    def get_kcal(self, obj):
        if obj.kcal_1g is None:
            return None
        weight = self._get_weight(obj)
        total_kcal = Decimal(weight) * Decimal(obj.kcal_1g)
        return f"{total_kcal:.2f}"

    def get_serving_unit_id(self, obj):
        unit = self._get_first_serving(obj)
        return unit.id if unit else None
    

class ProductServingUnitSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source='unit_name')
    label = serializers.CharField(source='custom_label', allow_null=True)

    class Meta:
        model = ProductServingUnit
        fields = ['id', 'unit_code', 'label', 'gram_weight']


class MealItemSerializer(serializers.ModelSerializer):
    total_kcal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_protein = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_fat = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_carbohydrates = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    display_salt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    serving_unit = ProductServingUnitSerializer(source='product_serving_unit', read_only=True)

    class Meta:
        model = MealItem
        fields = [
            'id', 'name', 'amount', 'calculated_gram_weight', 'serving_unit', 
            'total_kcal', 'total_protein', 'total_fat', 'total_carbohydrates', 'display_salt'
        ]


class FullMealSerializer(serializers.ModelSerializer):
    products = MealItemSerializer(many=True, read_only=True)

    meal_kcal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    meal_protein = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    meal_fat = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    meal_carbohydrates = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    meal_salt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = FullMeal
        fields = [
            'id', 'name', 'portion', 
            'meal_kcal', 'meal_protein', 'meal_fat', 'meal_carbohydrates', 'meal_salt',
            'products'
        ]


class MealCategorySerializer(serializers.ModelSerializer):
    direct_items = MealItemSerializer(source='direct_items_list', many=True, read_only=True)
    full_meals = FullMealSerializer(source='fullmeal', many=True, read_only=True)

    category_kcal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_protein = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_fat = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_carbohydrates = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    category_salt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = MealCategory
        fields = [
            'id', 'meal_type', 'name', 'order', 
            'category_kcal', 'category_protein', 'category_fat', 
            'category_carbohydrates', 'category_salt', 
            'full_meals', 'direct_items'
        ]

    def get_name(self, obj):
        if obj.meal_type <= 5:
            return None
        return obj.name


class AddProductToMealSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    date = serializers.DateField(required=True)
    meal_type = serializers.IntegerField(min_value=1, required=True)

    amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('1.00'))
    serving_unit_id = serializers.IntegerField(required=False, allow_null=True)
    custom_weight_g = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    custom_unit_label = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    calculated_gram_weight = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)


class CreateCustomMealSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    custom_name = serializers.CharField(max_length=100, required=True)


class DailyMealCalendarSerializer(serializers.ModelSerializer):
    meals = MealCategorySerializer(many=True, read_only=True)

    total_day_kcal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_protein = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_fat = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_carbohydrates = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_salt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DailyMealCalendar
        fields = [
            'id', 'date', 
            'total_day_kcal', 'total_day_protein', 'total_day_fat', 
            'total_day_carbohydrates', 'total_day_salt', 
            'meals'
        ]