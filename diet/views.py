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
)
from .models import DailyMealCalendar, MealCategory, FullMeal, MealItem, Product, ProductServingUnit

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
            Prefetch('meals', queryset=categories_qs)
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
            empty_data = {
                "id": None,
                "date": target_date.strftime("%Y-%m-%d"),
                "total_day_kcal": "0.00",
                "total_day_protein": "0.00",
                "total_day_fat": "0.00",
                "total_day_carbohydrates": "0.00",
                "total_day_salt": "0.00",
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


class ProductCursorPagination(CursorPagination):
    page_size = 20
    ordering = ('-popularity', '-id')

class ProductListView(ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductCursorPagination

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

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id 
                    FROM diet_product 
                    WHERE title ILIKE %s AND user_id IS NULL
                    """,
                    [f'%{clean_query}%']
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

        base_qs = (
            Product.objects
            .filter(user__isnull=True)
            .prefetch_related(self._get_servings_prefetch(request.user))
            .order_by('-popularity', '-id')
        )

        page = self.paginate_queryset(base_qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(base_qs, many=True)
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
            .prefetch_related('serving_units')
        )

