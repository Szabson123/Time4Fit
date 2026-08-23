from decimal import Decimal
from rest_framework import serializers
from django.db import transaction

from django.db.models import CharField
from django.contrib.postgres.fields import ArrayField

from .models import MealItem, MealCategory, FullMeal, DailyMealCalendar, ProductServingUnit, Product


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

    def _get_packaging_data(self, obj):
        if hasattr(obj, '_packaging_data'):
            return obj._packaging_data

        serving_unit = None
        if hasattr(obj, '_prefetched_objects_cache') and 'serving_units' in obj._prefetched_objects_cache:
            units = list(obj.serving_units.all())
            serving_unit = units[0] if len(units) > 0 else None
        else:
            serving_unit = obj.serving_units.first()

        if serving_unit:
            packaging = serving_unit.custom_label or serving_unit.get_unit_name_display() or serving_unit.unit_name
            weight_g = Decimal(str(serving_unit.gram_weight))
            serving_unit_id = serving_unit.id
        elif obj.package_whole_g is not None and obj.package_whole_g > 0:
            packaging = obj.package_name or "Opakowanie"
            weight_g = Decimal(str(obj.package_whole_g))
            serving_unit_id = None
        else:
            packaging = "100g"
            weight_g = Decimal("100.00")
            serving_unit_id = None

        kcal = round(weight_g * Decimal(str(obj.kcal_1g)), 2)

        data = {
            'packaging': packaging,
            'weight_g': weight_g,
            'kcal': kcal,
            'serving_unit_id': serving_unit_id,
        }
        obj._packaging_data = data
        return data

    def get_packaging(self, obj):
        return self._get_packaging_data(obj)['packaging']

    def get_weight_g(self, obj):
        return self._get_packaging_data(obj)['weight_g']

    def get_kcal(self, obj):
        return self._get_packaging_data(obj)['kcal']

    def get_serving_unit_id(self, obj):
        return self._get_packaging_data(obj)['serving_unit_id']



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
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = MealCategory
        fields = [
            'id', 'meal_type', 'meal_type_display', 'name', 'order', 
            'category_kcal', 'category_protein', 'category_fat', 
            'category_carbohydrates', 'category_salt', 
            'full_meals', 'direct_items'
        ]


class AddProductToMealSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    date = serializers.DateField(required=True)
    meal_type = serializers.IntegerField(min_value=1, required=True)

    amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=1.0)
    serving_unit_id = serializers.IntegerField(required=False, allow_null=True)
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