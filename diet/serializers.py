from rest_framework import serializers
from django.db import transaction

from django.db.models import CharField
from django.contrib.postgres.fields import ArrayField

from .models import MealItem, MealCategory, FullMeal, DailyMealCalendar, ProductServingUnit


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