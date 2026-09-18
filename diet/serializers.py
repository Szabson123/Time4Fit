from decimal import Decimal, ROUND_HALF_UP
import random
import json
from rest_framework import serializers
from django.db import transaction
from django.db.models import CharField, Q
from django.contrib.postgres.fields import ArrayField

from .models import (
    MealItem, MealCategory, FullMeal, DailyMealCalendar, WaterGlass,
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
    product_desc = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

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
            'image',
            'ingredients_image',
            'quantity_display',
            'category',
            'category_name',
            'product_desc',
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
            'recipes',
        ]

    def get_product_desc(self, obj):
        request = self.context.get('request')
        lang = 'pl'
        if request:
            user_profile_lang = getattr(getattr(request.user, 'profile', None), 'language', None)
            lang = (
                request.query_params.get('lang')
                or user_profile_lang
                or getattr(request.user, 'language', 'pl')
                or 'pl'
            )

        descs = list(obj.descriptions.all())
        if not descs:
            return None

        matching = [d for d in descs if d.language == lang]
        if not matching and lang != 'pl':
            matching = [d for d in descs if d.language == 'pl']
        if not matching:
            matching = descs

        return random.choice(matching).description

    def get_recipes(self, obj):
        dishes = obj.dishes.all()[:10]
        return [
            {
                "id": dish.id,
                "name": dish.name,
                "img": dish.img.url if dish.img else None,
                "category": dish.category.name if dish.category else None,
            }
            for dish in dishes
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
            'total_kcal', 'total_protein', 'total_fat', 'total_carbohydrates', 'display_salt',
            'is_quick_add'
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


class QuickAddMealItemSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    meal_type = serializers.IntegerField(required=True, min_value=1)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='Szybkie dodanie')
    kcal = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)
    protein = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), min_value=0)
    carbohydrates = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), min_value=0)
    fat = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), min_value=0)
    salt = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'), min_value=0)


class ProductCreateSerializer(serializers.ModelSerializer):
    values_per = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('100.00'))
    kcal = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)
    protein = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)
    carbohydrates = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)
    fat = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)
    salt = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=0)

    sugars = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    saturated_fat = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    fiber = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)

    ingredients_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    traces = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    serving_units = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    class Meta:
        model = Product
        fields = [
            'title', 'brand', 'barcode',
            'values_per', 'kcal', 'protein', 'carbohydrates', 'fat', 'salt',
            'sugars', 'saturated_fat', 'fiber',
            'package_name', 'package_whole_g', 'quantity_display',
            'allergens', 'countries',
            'ingredients_text', 'traces', 'serving_units',
            'image', 'ingredients_image', 'image_url'
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'dict'):
            data = data.dict()
        elif hasattr(data, 'copy'):
            data = data.copy()
        for json_field in ['allergens', 'traces', 'countries', 'serving_units']:
            val = data.get(json_field)
            if isinstance(val, str):
                try:
                    data[json_field] = json.loads(val)
                except (ValueError, TypeError):
                    pass
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        values_per = validated_data.pop('values_per', Decimal('100.00'))
        if not values_per or values_per <= 0:
            values_per = Decimal('100.00')

        kcal = validated_data.pop('kcal')
        protein = validated_data.pop('protein')
        fat = validated_data.pop('fat')
        carbohydrates = validated_data.pop('carbohydrates')
        salt = validated_data.pop('salt')
        sugars = validated_data.pop('sugars', None)
        saturated_fat = validated_data.pop('saturated_fat', None)
        fiber = validated_data.pop('fiber', None)

        ingredients_text = validated_data.pop('ingredients_text', '') or ''
        traces = validated_data.pop('traces', []) or []
        serving_units_data = validated_data.pop('serving_units', []) or []

        kcal_1g = (Decimal(str(kcal)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)
        protein_1g = (Decimal(str(protein)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)
        fat_1g = (Decimal(str(fat)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)
        carbohydrates_1g = (Decimal(str(carbohydrates)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)
        salt_1g = (Decimal(str(salt)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)

        sugars_1g = (Decimal(str(sugars)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP) if sugars is not None else None
        saturated_fat_1g = (Decimal(str(saturated_fat)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP) if saturated_fat is not None else None
        fiber_1g = (Decimal(str(fiber)) / values_per).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP) if fiber is not None else None

        product = Product.objects.create(
            user=user,
            kcal_1g=kcal_1g,
            protein_1g=protein_1g,
            fat_1g=fat_1g,
            carbohydrates_1g=carbohydrates_1g,
            salt_1g=salt_1g,
            sugars_1g=sugars_1g,
            saturated_fat_1g=saturated_fat_1g,
            fiber_1g=fiber_1g,
            **validated_data
        )

        if product.image and not product.image_url:
            product.image_url = product.image.url
            product.save(update_fields=['image_url'])

        ProductAdditionalInfo.objects.create(
            product=product,
            ingredients_text=ingredients_text,
            traces=traces,
            is_complete_profile=True
        )

        for su_data in serving_units_data:
            gram_weight = su_data.get('gram_weight')
            if gram_weight:
                custom_label = su_data.get('custom_label') or su_data.get('label') or ''
                unit_name = su_data.get('unit_name') or su_data.get('unit_code') or 'custom'
                ProductServingUnit.objects.create(
                    product=product,
                    unit_name=unit_name,
                    custom_label=custom_label,
                    gram_weight=Decimal(str(gram_weight)),
                    created_by=user,
                    is_global=False
                )

        return product


class CreateCustomMealSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    custom_name = serializers.CharField(max_length=100, required=True)


class WaterGlassSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterGlass
        fields = ['id', 'amount_ml', 'created_at']


class DailyMealCalendarSerializer(serializers.ModelSerializer):
    meals = MealCategorySerializer(many=True, read_only=True)

    total_day_kcal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_protein = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_fat = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_carbohydrates = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_day_salt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    water_intake_ml = serializers.IntegerField(read_only=True)
    standard_water_intake_ml = serializers.SerializerMethodField()
    daily_water_goal_ml = serializers.SerializerMethodField()
    water_glasses = WaterGlassSerializer(many=True, read_only=True)

    class Meta:
        model = DailyMealCalendar
        fields = [
            'id', 'date', 
            'total_day_kcal', 'total_day_protein', 'total_day_fat', 
            'total_day_carbohydrates', 'total_day_salt', 
            'water_intake_ml', 'standard_water_intake_ml', 'daily_water_goal_ml',
            'water_glasses',
            'meals'
        ]

    def get_standard_water_intake_ml(self, obj):
        user = getattr(obj, 'user', None)
        if not user and 'request' in self.context:
            user = self.context['request'].user
        profile = getattr(user, 'profile', None)
        if profile:
            profile.refresh_from_db()
            return profile.standard_water_intake_ml
        return 250

    def get_daily_water_goal_ml(self, obj):
        user = getattr(obj, 'user', None)
        if not user and 'request' in self.context:
            user = self.context['request'].user
        profile = getattr(user, 'profile', None)
        if profile:
            profile.refresh_from_db()
            return profile.daily_water_goal_ml
        return 2000


class DailyWaterIntakeUpdateSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    amount_ml = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    glass_id = serializers.IntegerField(required=False, allow_null=True)
    action = serializers.ChoiceField(
        choices=['add', 'subtract', 'set', 'reset', 'delete'],
        default='add',
        required=False
    )


class DailyWaterIntakeResponseSerializer(serializers.Serializer):
    date = serializers.DateField()
    water_intake_ml = serializers.IntegerField()
    standard_water_intake_ml = serializers.IntegerField()
    daily_water_goal_ml = serializers.IntegerField()
    water_glasses = WaterGlassSerializer(many=True, required=False)