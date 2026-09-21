from decimal import Decimal, ROUND_HALF_UP
from .models import Product, MealItem, DailyMealCalendar, MealCategory, FullMeal

from django.db.models import Prefetch, Sum, ExpressionWrapper, F, DecimalField, Value
from django.db.models.functions import Coalesce


class ProductService:
    @staticmethod
    def normalize_to_1g(value: Decimal, total_mass: Decimal) -> Decimal:
        if not total_mass or total_mass <= 0:
            return Decimal('0.00000')
        return (value / total_mass).quantize(Decimal('1.00000'), rounding=ROUND_HALF_UP)

    @classmethod
    def _prepare_nutrition_data(cls, data, label_type, packaging_size):
        divider = Decimal('100.00') if label_type == 'EU' else packaging_size
        
        fields = ['kcal', 'protein', 'fat', 'carbohydrates']
        
        for field in fields:
            if field in data:
                raw_value = data.pop(field)
                data[f'{field}_1g'] = cls.normalize_to_1g(raw_value, divider)
        
        if 'sodium_salt' in data:
            raw_sodium_salt = data.pop('sodium_salt')
            if label_type == 'US':
                salt_g = (raw_sodium_salt / Decimal('1000')) * Decimal('2.5')
            else:
                salt_g = raw_sodium_salt
            
            data['salt_1g'] = cls.normalize_to_1g(salt_g, divider)

        return data

    @classmethod
    def create_product(cls, user, validated_data):
        allergens = validated_data.pop('allergens', [])
        
        label_type = validated_data.get('label_type')
        packaging_size = validated_data.get('packaging_size')
        
        processed_data = cls._prepare_nutrition_data(validated_data, label_type, packaging_size)
        
        product = Product.objects.create(user=user, **processed_data)
        
        if allergens:
            product.allergens.set(allergens)
            
        return product
    
    @classmethod
    def update_product(cls, instance, validated_data):
        allergens = validated_data.pop('allergens', None)
        
        label_type = validated_data.get('label_type', instance.label_type)
        packaging_size = validated_data.get('packaging_size', instance.packaging_size)

        processed_data = cls._prepare_nutrition_data(validated_data, label_type, packaging_size)

        for attr, value in processed_data.items():
            setattr(instance, attr, value)
        
        instance.save()

        if allergens is not None:
            instance.allergens.set(allergens)

        return instance


def get_daily_meal_plan(user, target_date):
    annotated_items = MealItem.objects.with_neutriens()

    calendar_day = DailyMealCalendar.objects.filter(
        user=user,
        date=target_date
    ).prefetch_related(
        Prefetch(
            'meal',
            MealCategory.objects.prefetch_related(
                Prefetch(('items', annotated_items)),
                Prefetch('fullmeal', FullMeal.objects.prefetch_related(
                    Prefetch('products', annotated_items)
                ))
            )
        )
    ).first()

    if not calendar_day:
        return None

    day_totals = MealItem.objects.filter(
        meal_category__calendar=calendar_day
    ).aggregate(
        total_kcal=Coalesce(Sum(ExpressionWrapper(F('kcal_1g') * F('amount_g'), output_field=DecimalField())), Value(0.0)),
        total_protein=Coalesce(Sum(ExpressionWrapper(F('protein_1g') * F('amount_g'), output_field=DecimalField())), Value(0.0)),
        total_fat=Coalesce(Sum(ExpressionWrapper(F('fat_1g') * F('amount_g'), output_field=DecimalField())), Value(0.0)),
        total_carbohydrates=Coalesce(Sum(ExpressionWrapper(F('carbohydrates_1g') * F('amount_g'), output_field=DecimalField())), Value(0.0)),
        total_salt=Coalesce(Sum(ExpressionWrapper(F('salt_1g') * F('amount_g'), output_field=DecimalField())), Value(0.0))
    )

    return {
        "calendar": calendar_day,
        "totals": day_totals
    }


class MacroCalculatorService:
    # PAL multipliers
    ACTIVITY_MULTIPLIERS = {
        'sedentary': Decimal('1.20'),
        'lightly_active': Decimal('1.375'),
        'moderately_active': Decimal('1.55'),
        'very_active': Decimal('1.725'),
    }

    # Goal adjustment percentage
    GOAL_ADJUSTMENTS = {
        'maintenance': Decimal('1.00'),       # 0%
        'reduction': Decimal('0.85'),         # -15%
        'muscle_gain': Decimal('1.10'),       # +10%
    }

    # Protein per kg body weight depending on goal
    PROTEIN_PER_KG = {
        'maintenance': Decimal('1.60'),
        'reduction': Decimal('2.00'),
        'muscle_gain': Decimal('1.80'),
    }

    @classmethod
    def calculate_bmr(cls, gender: str, weight_kg: Decimal, height_cm: Decimal, age: int, body_fat_percentage: Decimal = None) -> Decimal:
        weight_kg = Decimal(str(weight_kg))
        height_cm = Decimal(str(height_cm))
        age = Decimal(str(age))

        if body_fat_percentage is not None and body_fat_percentage > 0:
            # Katch-McArdle formula based on Lean Body Mass (LBM)
            bf = Decimal(str(body_fat_percentage))
            lbm = weight_kg * (Decimal('1.00') - (bf / Decimal('100.00')))
            bmr = Decimal('370.00') + (Decimal('21.60') * lbm)
        else:
            # Mifflin-St Jeor formula
            if gender == 'male':
                bmr = (Decimal('10.00') * weight_kg) + (Decimal('6.25') * height_cm) - (Decimal('5.00') * age) + Decimal('5.00')
            else:
                bmr = (Decimal('10.00') * weight_kg) + (Decimal('6.25') * height_cm) - (Decimal('5.00') * age) - Decimal('161.00')

        return bmr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_tdee(cls, bmr: Decimal, activity_level: str) -> Decimal:
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level, Decimal('1.20'))
        tdee = bmr * multiplier
        return tdee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_target_macros(cls, tdee: Decimal, goal: str, weight_kg: Decimal) -> dict:
        weight_kg = Decimal(str(weight_kg))
        goal_mult = cls.GOAL_ADJUSTMENTS.get(goal, Decimal('1.00'))
        target_calories = (tdee * goal_mult).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Protein: based on goal & weight in kg
        protein_factor = cls.PROTEIN_PER_KG.get(goal, Decimal('1.80'))
        target_protein_g = (weight_kg * protein_factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        protein_kcal = target_protein_g * Decimal('4.00')

        # Fat: 25% of target calories
        fat_kcal = target_calories * Decimal('0.25')
        target_fat_g = (fat_kcal / Decimal('9.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Carbohydrates: remaining calories
        carb_kcal = target_calories - protein_kcal - (target_fat_g * Decimal('9.00'))
        if carb_kcal < Decimal('0.00'):
            carb_kcal = Decimal('0.00')
        target_carbohydrates_g = (carb_kcal / Decimal('4.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            "target_calories": target_calories,
            "target_protein_g": target_protein_g,
            "target_fat_g": target_fat_g,
            "target_carbohydrates_g": target_carbohydrates_g,
        }

    @classmethod
    def calculate_all(cls, gender: str, age: int, weight_kg: Decimal, height_cm: Decimal, activity_level: str, goal: str, body_fat_percentage: Decimal = None) -> dict:
        bmr = cls.calculate_bmr(gender, weight_kg, height_cm, age, body_fat_percentage)
        tdee = cls.calculate_tdee(bmr, activity_level)
        macros = cls.calculate_target_macros(tdee, goal, weight_kg)
        return {
            "bmr": bmr,
            "tdee": tdee,
            **macros,
        }