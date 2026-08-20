from django.shortcuts import render
from django.db.models import Prefetch, F, ExpressionWrapper, DecimalField, Sum, CharField, Q, Value
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework import status

from .serializers import DailyMealCalendarSerializer
from .models import DailyMealCalendar, MealCategory, FullMeal, MealItem

from datetime import datetime

class DailyMealCalendarDetailView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyMealCalendarSerializer

    def get_queryset(self):
        meal_items_qs = MealItem.objects.with_nutrients().select_related('product_serving_unit')

        full_meals_qs = FullMeal.objects.annotate(
            meal_kcal=Coalesce(Sum('products__kcal_1g' * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_protein=Coalesce(Sum('products__protein_1g' * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_fat=Coalesce(Sum('products__fat_1g' * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_carbohydrates=Coalesce(Sum('products__carbohydrates_1g' * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            meal_salt=Coalesce(Sum('products__salt_1g' * F('products__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).prefetch_related(
            Prefetch('products', queryset=meal_items_qs)
        )

        categories_qs = MealCategory.objects.annotate(
            category_kcal=Coalesce(Sum('items__kcal_1g' * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_protein=Coalesce(Sum('items__protein_1g' * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_fat=Coalesce(Sum('items__fat_1g' * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_carbohydrates=Coalesce(Sum('items__carbohydrates_1g' * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            category_salt=Coalesce(Sum('items__salt_1g' * F('items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
        ).prefetch_related(
            Prefetch('items', queryset=meal_items_qs.filter(full_meal__isnull=True), to_attr='direct_items_list'),
            Prefetch('fullmeal', queryset=full_meals_qs)
        )

        return DailyMealCalendar.objects.filter(
            user=self.request.user
        ).annotate(
            total_day_kcal=Coalesce(Sum('meals__items__kcal_1g' * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_protein=Coalesce(Sum('meals__items__protein_1g' * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_fat=Coalesce(Sum('meals__items__fat_1g' * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_carbohydrates=Coalesce(Sum('meals__items__carbohydrates_1g' * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
            total_day_salt=Coalesce(Sum('meals__items__salt_1g' * F('meals__items__calculated_gram_weight')), Value(0.0), output_field=DecimalField()),
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