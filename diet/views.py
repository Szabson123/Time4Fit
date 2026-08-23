from django.shortcuts import render
from rest_framework.pagination import CursorPagination
from django.db.models import OuterRef, Subquery, Value, F, DecimalField, ExpressionWrapper, Max
from django.db.models.functions import Coalesce
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework import status

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

        calendar_day = get_object_or_404(self.get_queryset(), date=target_date)
        serializer = self.get_serializer(calendar_day)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        amount = data.get('amount', 1.0)
        serving_unit_id = data.get('serving_unit_id')
        calc_gram_weight = data.get('calculated_gram_weight')

        product = get_object_or_404(Product, id=product_id)

        calendar_day, _ = DailyMealCalendar.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        if meal_type <= 5:
            dict_choices = dict(MealCategory.MEAL_TYPE_CHOICES)
            meal_name = dict_choices.get(meal_type)
            meal_category = MealCategory.objects.filter(
                calendar=calendar_day,
                meal_type=meal_type
            ).first()
            if not meal_category:
                meal_category = MealCategory.objects.create(
                    calendar=calendar_day,
                    meal_type=meal_type,
                    name=meal_name,
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
        if serving_unit_id:
            serving_unit = get_object_or_404(ProductServingUnit, id=serving_unit_id, product=product)

        if calc_gram_weight is not None:
            final_gram_weight = calc_gram_weight
        elif serving_unit:
            final_gram_weight = amount * serving_unit.gram_weight
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
    ordering = ('title', 'id')

class ProductListView(ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductCursorPagination

    def get_queryset(self):
        first_serving = ProductServingUnit.objects.filter(
            product=OuterRef('pk')
        ).order_by('id')

        return (
            Product.objects
            .filter(user__isnull=True)
            .annotate(
                first_unit_id=Subquery(first_serving.values('id')[:1]),
                first_unit_label=Subquery(first_serving.values('custom_label')[:1]),
                first_unit_name=Subquery(first_serving.values('unit_name')[:1]),
                first_unit_weight=Subquery(first_serving.values('gram_weight')[:1]),
            )
            .annotate(
                calc_weight=Coalesce(
                    F('first_unit_weight'),
                    F('package_whole_g'),
                    Value(100.0),
                    output_field=DecimalField()
                )
            )
            .annotate(
                calc_kcal=ExpressionWrapper(
                    F('calc_weight') * F('kcal_1g'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            .only('id', 'title', 'brand', 'image_url', 'kcal_1g', 'package_name', 'package_whole_g')
            .order_by('title', 'id')
        )


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

