from decimal import Decimal
from django.shortcuts import render
from rest_framework.pagination import CursorPagination
from django.db.models import OuterRef, Subquery, Value, F, DecimalField, ExpressionWrapper, Max, Prefetch, Sum, Q
from django.db.models.functions import Coalesce
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status

import time
from django.db import connection


from django.db import transaction
from .serializers import (
    DailyMealCalendarSerializer,
    AddProductToMealSerializer,
    MealItemSerializer,
    CreateCustomMealSerializer,
    MealCategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    DailyWaterIntakeUpdateSerializer,
    DailyWaterIntakeResponseSerializer,
    QuickAddMealItemSerializer,
    ProductCreateSerializer,
    UserDailyMacrosSerializer,
)
from .models import DailyMealCalendar, MealCategory, FullMeal, MealItem, Product, ProductServingUnit, WaterGlass
from user_profile.models import UserMacroProfile
from .tasks import trigger_product_popularity_increment, trigger_generate_product_descriptions

from datetime import datetime


def get_empty_meal_slot(meal_type: int):
    return {
        "id": None,
        "meal_type": meal_type,
        "name": None,
        "order": meal_type,
        "category_kcal": "0.00",
        "category_protein": "0.00",
        "category_fat": "0.00",
        "category_carbohydrates": "0.00",
        "category_salt": "0.00",
        "full_meals": [],
        "direct_items": [],
    }


class DailyMealCalendarDetailView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyMealCalendarSerializer

    def get_queryset(self):
        meal_items_qs = MealItem.objects.with_nutrients().select_related('product_serving_unit')

        full_meals_qs = FullMeal.objects.annotate(
            meal_kcal=Coalesce(Sum(F('products__kcal_1g') * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_protein=Coalesce(Sum(F('products__protein_1g') * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_fat=Coalesce(Sum(F('products__fat_1g') * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_carbohydrates=Coalesce(Sum(F('products__carbohydrates_1g') * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_salt=Coalesce(Sum(F('products__salt_1g') * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).prefetch_related(
            Prefetch('products', queryset=meal_items_qs)
        )

        categories_qs = MealCategory.objects.annotate(
            category_kcal=Coalesce(Sum(F('items__kcal_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_protein=Coalesce(Sum(F('items__protein_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_fat=Coalesce(Sum(F('items__fat_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_carbohydrates=Coalesce(Sum(F('items__carbohydrates_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_salt=Coalesce(Sum(F('items__salt_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).prefetch_related(
            Prefetch('items', queryset=meal_items_qs.filter(full_meal__isnull=True), to_attr='direct_items_list'),
            Prefetch('fullmeal', queryset=full_meals_qs)
        )

        return DailyMealCalendar.objects.filter(
            user=self.request.user
        ).annotate(
            total_day_kcal=Coalesce(Sum(F('meals__items__kcal_1g') * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_protein=Coalesce(Sum(F('meals__items__protein_1g') * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_fat=Coalesce(Sum(F('meals__items__fat_1g') * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_carbohydrates=Coalesce(Sum(F('meals__items__carbohydrates_1g') * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_salt=Coalesce(Sum(F('meals__items__salt_1g') * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).prefetch_related(
            Prefetch('meals', queryset=categories_qs),
            Prefetch('water_glasses', queryset=WaterGlass.objects.order_by('created_at', 'id'))
        )

    def get(self, request, date_str=None):
        target_date_str = date_str or request.query_params.get('date')

        if not target_date_str:
            return Response({"detail": "Brak wymaganego parametru daty (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Niepoprawny format daty."}, status=status.HTTP_400_BAD_REQUEST)

        calendar_day = self.get_queryset().filter(date=target_date).first()

        if not calendar_day:
            profile = getattr(request.user, 'profile', None)
            if profile:
                profile.refresh_from_db()
            empty_data = {
                "id": None,
                "date": target_date.strftime("%Y-%m-%d"),
                "total_day_kcal": "0.00",
                "total_day_protein": "0.00",
                "total_day_fat": "0.00",
                "total_day_carbohydrates": "0.00",
                "total_day_salt": "0.00",
                "water_intake_ml": 0,
                "standard_water_intake_ml": getattr(profile, 'standard_water_intake_ml', 250) if profile else 250,
                "daily_water_goal_ml": getattr(profile, 'daily_water_goal_ml', 2000) if profile else 2000,
                "water_glasses": [],
                "meals": [get_empty_meal_slot(i) for i in range(1, 6)],
            }
            return Response(empty_data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(calendar_day)
        data = serializer.data

        existing_meals = data.get('meals', [])
        existing_meals_by_type = {m['meal_type']: m for m in existing_meals}

        filled_meals = []
        for i in range(1, 6):
            if i in existing_meals_by_type:
                filled_meals.append(existing_meals_by_type[i])
            else:
                filled_meals.append(get_empty_meal_slot(i))

        custom_meals = [m for m in existing_meals if m['meal_type'] >= 6]
        custom_meals.sort(key=lambda m: (m.get('order') or m['meal_type'], m['meal_type']))

        data['meals'] = filled_meals + custom_meals
        return Response(data, status=status.HTTP_200_OK)


class DailyWaterIntakeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyWaterIntakeUpdateSerializer

    def get(self, request, *args, **kwargs):
        target_date_str = request.query_params.get('date')
        if not target_date_str:
            return Response({"detail": "Brak wymaganego parametru daty (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Niepoprawny format daty."}, status=status.HTTP_400_BAD_REQUEST)

        calendar_day = DailyMealCalendar.objects.filter(user=request.user, date=target_date).prefetch_related('water_glasses').first()
        water_intake_ml = calendar_day.water_intake_ml if calendar_day else 0
        water_glasses = list(calendar_day.water_glasses.all()) if calendar_day else []

        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.refresh_from_db()
        standard_water_intake_ml = getattr(profile, 'standard_water_intake_ml', 250) if profile else 250
        daily_water_goal_ml = getattr(profile, 'daily_water_goal_ml', 2000) if profile else 2000

        data = {
            "date": target_date,
            "water_intake_ml": water_intake_ml,
            "standard_water_intake_ml": standard_water_intake_ml,
            "daily_water_goal_ml": daily_water_goal_ml,
            "water_glasses": water_glasses,
        }
        return Response(DailyWaterIntakeResponseSerializer(data).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_date = data['date']
        action = data.get('action', 'add')
        amount_ml = data.get('amount_ml')
        glass_id = data.get('glass_id')

        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.refresh_from_db()
        standard_water_intake_ml = getattr(profile, 'standard_water_intake_ml', 250) if profile else 250
        daily_water_goal_ml = getattr(profile, 'daily_water_goal_ml', 2000) if profile else 2000

        calendar_day, _ = DailyMealCalendar.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        amount = amount_ml if amount_ml is not None else standard_water_intake_ml

        if action == 'add':
            WaterGlass.objects.create(calendar=calendar_day, amount_ml=amount)
            calendar_day.water_intake_ml += amount
        elif action == 'delete':
            if glass_id:
                glass = calendar_day.water_glasses.filter(id=glass_id).first()
                if glass:
                    calendar_day.water_intake_ml = max(0, calendar_day.water_intake_ml - glass.amount_ml)
                    glass.delete()
        elif action == 'subtract':
            if glass_id:
                glass = calendar_day.water_glasses.filter(id=glass_id).first()
                if glass:
                    calendar_day.water_intake_ml = max(0, calendar_day.water_intake_ml - glass.amount_ml)
                    glass.delete()
            else:
                last_glass = calendar_day.water_glasses.order_by('-created_at', '-id').first()
                if last_glass:
                    calendar_day.water_intake_ml = max(0, calendar_day.water_intake_ml - last_glass.amount_ml)
                    last_glass.delete()
                else:
                    calendar_day.water_intake_ml = max(0, calendar_day.water_intake_ml - amount)
        elif action == 'set':
            calendar_day.water_glasses.all().delete()
            if amount > 0:
                WaterGlass.objects.create(calendar=calendar_day, amount_ml=amount)
            calendar_day.water_intake_ml = max(0, amount)
        elif action == 'reset':
            calendar_day.water_glasses.all().delete()
            calendar_day.water_intake_ml = 0

        calendar_day.save()

        response_data = {
            "date": target_date,
            "water_intake_ml": calendar_day.water_intake_ml,
            "standard_water_intake_ml": standard_water_intake_ml,
            "daily_water_goal_ml": daily_water_goal_ml,
            "water_glasses": calendar_day.water_glasses.all(),
        }
        return Response(DailyWaterIntakeResponseSerializer(response_data).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        glass_id = request.query_params.get('glass_id') or request.data.get('glass_id')
        target_date_str = request.query_params.get('date') or request.data.get('date')
        if not target_date_str:
            return Response({"detail": "Brak wymaganego parametru daty (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Niepoprawny format daty."}, status=status.HTTP_400_BAD_REQUEST)

        calendar_day = DailyMealCalendar.objects.filter(user=request.user, date=target_date).first()
        if not calendar_day:
            return Response({"detail": "Brak wpisu dla tej daty."}, status=status.HTTP_404_NOT_FOUND)

        if glass_id:
            glass = calendar_day.water_glasses.filter(id=glass_id).first()
            if not glass:
                return Response({"detail": "Szklanka o podanym ID nie istnieje."}, status=status.HTTP_404_NOT_FOUND)
            calendar_day.water_intake_ml = max(0, calendar_day.water_intake_ml - glass.amount_ml)
            glass.delete()
        else:
            calendar_day.water_glasses.all().delete()
            calendar_day.water_intake_ml = 0

        calendar_day.save()

        profile = getattr(request.user, 'profile', None)
        if profile:
            profile.refresh_from_db()
        standard_water_intake_ml = getattr(profile, 'standard_water_intake_ml', 250) if profile else 250
        daily_water_goal_ml = getattr(profile, 'daily_water_goal_ml', 2000) if profile else 2000

        response_data = {
            "date": target_date,
            "water_intake_ml": calendar_day.water_intake_ml,
            "standard_water_intake_ml": standard_water_intake_ml,
            "daily_water_goal_ml": daily_water_goal_ml,
            "water_glasses": calendar_day.water_glasses.all(),
        }
        return Response(DailyWaterIntakeResponseSerializer(response_data).data, status=status.HTTP_200_OK)


class AddProductToMealView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddProductToMealSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        product_id = data['product_id']
        target_date = data['date']
        meal_type = data['meal_type']
        amount = data.get('amount', Decimal('1.00'))
        serving_unit_id = data.get('serving_unit_id')
        custom_weight_g = data.get('custom_weight_g')
        custom_unit_label = data.get('custom_unit_label')
        calc_gram_weight = data.get('calculated_gram_weight')

        product = get_object_or_404(Product, id=product_id)

        calendar_day, _ = DailyMealCalendar.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        if meal_type <= 5:
            meal_category = MealCategory.objects.filter(
                calendar=calendar_day,
                meal_type=meal_type
            ).first()
            if not meal_category:
                meal_category = MealCategory.objects.create(
                    calendar=calendar_day,
                    meal_type=meal_type,
                    name=None,
                    order=meal_type
                )
        else:
            meal_category = MealCategory.objects.filter(
                calendar=calendar_day,
                meal_type=meal_type
            ).first()
            if not meal_category:
                return Response(
                    {"detail": f"Posiłek o numerze {meal_type} nie istnieje w wybranym dniu. Utwórz go najpierw za pomocą /diet/add-meal/."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serving_unit = None

        if custom_weight_g is not None:
            # Użytkownik ręcznie wpisał wagę (np. 40g) -> zapisujemy/przypisujemy ProductServingUnit dla tego usera
            label = (custom_unit_label or "").strip()
            if not label:
                if custom_weight_g == int(custom_weight_g):
                    label = f"{int(custom_weight_g)}g"
                else:
                    label = f"{custom_weight_g}g"

            serving_unit, _ = ProductServingUnit.objects.get_or_create(
                product=product,
                created_by=request.user,
                gram_weight=custom_weight_g,
                defaults={
                    'unit_name': 'custom',
                    'custom_label': label,
                    'is_global': False,
                }
            )
            final_gram_weight = amount * custom_weight_g
        elif serving_unit_id:
            serving_unit = get_object_or_404(
                ProductServingUnit.objects.filter(Q(is_global=True) | Q(created_by=request.user)),
                id=serving_unit_id,
                product=product
            )
            final_gram_weight = amount * serving_unit.gram_weight
        elif calc_gram_weight is not None:
            final_gram_weight = calc_gram_weight
        else:
            # Domyślne dodanie (np. plusik lub podana waga w amount)
            default_serving = product.serving_units.filter(
                Q(is_global=True) | Q(created_by=request.user)
            ).order_by('id').first()

            if default_serving:
                serving_unit = default_serving
                final_gram_weight = amount * default_serving.gram_weight
            elif product.package_whole_g is not None:
                final_gram_weight = amount * product.package_whole_g
            else:
                if amount == Decimal('1.00') or amount == Decimal('1.0') or amount == 1:
                    final_gram_weight = Decimal('100.00')
                else:
                    final_gram_weight = amount

        meal_item = MealItem.objects.create(
            meal_category=meal_category,
            original_product=product,
            name=product.title,
            kcal_1g=product.kcal_1g,
            protein_1g=product.protein_1g,
            fat_1g=product.fat_1g,
            carbohydrates_1g=product.carbohydrates_1g,
            salt_1g=product.salt_1g,
            product_serving_unit=serving_unit,
            amount=amount,
            calculated_gram_weight=final_gram_weight,
        )

        trigger_product_popularity_increment(product.id, points=5)

        item_qs = MealItem.objects.with_nutrients().filter(id=meal_item.id).first()
        output_serializer = MealItemSerializer(item_qs)

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CreateCustomMealView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCustomMealSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        target_date = data['date']
        custom_name = data['custom_name'].strip()

        calendar_day, _ = DailyMealCalendar.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        max_custom_type = MealCategory.objects.filter(
            calendar=calendar_day,
            meal_type__gte=6
        ).aggregate(Max('meal_type'))['meal_type__max']

        if max_custom_type is None:
            next_meal_type = 6
        else:
            next_meal_type = max_custom_type + 1

        meal_category = MealCategory.objects.create(
            calendar=calendar_day,
            meal_type=next_meal_type,
            name=custom_name,
            order=next_meal_type
        )

        categories_qs = MealCategory.objects.filter(id=meal_category.id).annotate(
            category_kcal=Coalesce(Sum(F('items__kcal_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_protein=Coalesce(Sum(F('items__protein_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_fat=Coalesce(Sum(F('items__fat_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_carbohydrates=Coalesce(Sum(F('items__carbohydrates_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_salt=Coalesce(Sum(F('items__salt_1g') * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).first()

        out_serializer = MealCategorySerializer(categories_qs)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class QuickAddMealItemView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuickAddMealItemSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_date = data['date']
        meal_type = data['meal_type']
        name = (data.get('name') or "").strip() or "Szybkie dodanie"
        kcal = data['kcal']
        protein = data.get('protein', Decimal('0.00'))
        carbohydrates = data.get('carbohydrates', Decimal('0.00'))
        fat = data.get('fat', Decimal('0.00'))
        salt = data.get('salt', Decimal('0.00'))

        calendar_day, _ = DailyMealCalendar.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        if meal_type <= 5:
            meal_category = MealCategory.objects.filter(
                calendar=calendar_day,
                meal_type=meal_type
            ).first()
            if not meal_category:
                meal_category = MealCategory.objects.create(
                    calendar=calendar_day,
                    meal_type=meal_type,
                    name=None,
                    order=meal_type
                )
        else:
            meal_category = MealCategory.objects.filter(
                calendar=calendar_day,
                meal_type=meal_type
            ).first()
            if not meal_category:
                return Response(
                    {"detail": f"Posiłek o numerze {meal_type} nie istnieje w wybranym dniu. Utwórz go najpierw za pomocą /diet/add-meal/."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        meal_item = MealItem.objects.create(
            meal_category=meal_category,
            original_product=None,
            original_recipe=None,
            name=name,
            kcal_1g=kcal,
            protein_1g=protein,
            fat_1g=fat,
            carbohydrates_1g=carbohydrates,
            salt_1g=salt,
            amount=Decimal('1.00'),
            calculated_gram_weight=Decimal('1.00'),
            is_quick_add=True
        )

        item_qs = MealItem.objects.with_nutrients().filter(id=meal_item.id).first()
        output_serializer = MealItemSerializer(item_qs)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class ProductCursorPagination(CursorPagination):
    page_size = 20
    ordering = ('-popularity', '-id')

class ProductListView(ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductCursorPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_servings_prefetch(self, user=None):
        filter_q = Q(is_global=True)
        if user and user.is_authenticated:
            filter_q |= Q(created_by=user)
        return Prefetch(
            'serving_units',
            queryset=ProductServingUnit.objects.filter(filter_q).order_by('id'),
            to_attr='prefetched_servings'
        )

    def list(self, request, *args, **kwargs):
        raw_query = request.query_params.get('search', '').strip()

        if raw_query:
            clean_query = raw_query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

            user_clause = "AND (user_id IS NULL OR user_id = %s)" if (request.user and request.user.is_authenticated) else "AND user_id IS NULL"
            params = [f'%{clean_query}%', request.user.id] if (request.user and request.user.is_authenticated) else [f'%{clean_query}%']

            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id 
                    FROM diet_product 
                    WHERE title ILIKE %s {user_clause}
                    """,
                    params
                )
                matching_ids = [row[0] for row in cursor.fetchall()]

            if not matching_ids:
                return Response([])

            qs = (
                Product.objects
                .filter(id__in=matching_ids)
                .prefetch_related(self._get_servings_prefetch(request.user))
                .order_by('-popularity', '-id')[:50]
            )

            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)

        user_filter = Q(user__isnull=True)
        if request.user and request.user.is_authenticated:
            user_filter |= Q(user=request.user)

        base_qs = (
            Product.objects
            .filter(user_filter)
            .prefetch_related(self._get_servings_prefetch(request.user))
            .order_by('-popularity', '-id')
        )

        page = self.paginate_queryset(base_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(base_qs, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Wymagane logowanie do utworzenia produktu."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ProductCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        product_qs = (
            Product.objects
            .filter(id=product.id)
            .select_related('category', 'additional_info')
            .prefetch_related('serving_units', 'descriptions', 'dishes', 'dishes__category')
            .first()
        )
        out_serializer = ProductDetailSerializer(product_qs, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class ProductCreateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ProductCreateSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        product_qs = (
            Product.objects
            .filter(id=product.id)
            .select_related('category', 'additional_info')
            .prefetch_related('serving_units', 'descriptions', 'dishes', 'dishes__category')
            .first()
        )
        out_serializer = ProductDetailSerializer(product_qs, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

        
class ProductDetailView(RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return (
            Product.objects
            .filter(Q(user__isnull=True) | Q(user=self.request.user))
            .select_related('category', 'additional_info')
            .prefetch_related('serving_units', 'descriptions', 'dishes', 'dishes__category')
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        trigger_product_popularity_increment(instance.id, points=2)
        if not instance.descriptions.all():
            trigger_generate_product_descriptions(instance.id)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductDetailByBarcodeView(RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'barcode'
    lookup_url_kwarg = 'barcode'

    def get_queryset(self):
        return (
            Product.objects
            .filter(Q(user__isnull=True) | Q(user=self.request.user))
            .select_related('category', 'additional_info')
            .prefetch_related('serving_units', 'descriptions', 'dishes', 'dishes__category')
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        trigger_product_popularity_increment(instance.id, points=2)
        if not instance.descriptions.all():
            trigger_generate_product_descriptions(instance.id)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DailyUserMacrosView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDailyMacrosSerializer

    def get_object(self):
        try:
            return UserMacroProfile.objects.get(user=self.request.user)
        except UserMacroProfile.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response(
                {"detail": "Profil makroskładników nie został jeszcze skonfigurowany.", "configured": False},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance:
            serializer = self.get_serializer(instance, data=request.data)
            created = False
        else:
            serializer = self.get_serializer(data=request.data)
            created = True

        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        out_serializer = self.get_serializer(profile)
        return Response(
            out_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def put(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response(
                {"detail": "Profil makroskładników nie został jeszcze skonfigurowany. Użyj metody POST.", "configured": False},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(self.get_serializer(profile).data, status=status.HTTP_200_OK)

