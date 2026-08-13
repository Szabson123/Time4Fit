from django.shortcuts import render
from django.db.models import Prefetch, F, ExpressionWrapper, DecimalField, Sum, CharField, Q, Value
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, viewsets, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from .serializers import ProductCategorySerializer, DishSerializer, DailyMealCalendarSerializer, ProductCreateSerializer, ProductListSerializer, AllergenSerializer, DishCreateSerializer, RetriveDishSerializer
from .models import Product, Allergen, ProductCategory, Dish, DailyMealCalendar, MealCategory, FullMeal, MealItem
from .filters import SmartHybridSearchFilter
from .permissions import IsProductOwner

from datetime import datetime


class CategoryHelper(generics.ListAPIView):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()


class AllergensHelper(generics.ListAPIView):
    serializer_class = AllergenSerializer
    queryset = Allergen.objects.all()


class CustomPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 60


class CreateProductView(generics.CreateAPIView):
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]


class ListMyProductView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated, IsProductOwner]
    pagination_class = CustomPagination
    
    filter_backends = [SmartHybridSearchFilter, OrderingFilter]

    ordering_fields = ['total_kcal', 'total_protein', 'total_fat', 'total_carbohydrates', 'display_salt']

    def get_queryset(self):
        return (Product.objects
                .filter(user=self.request.user)
                .with_nutrients()
                .select_related('category', 'packaging_type')
                .prefetch_related(
                    Prefetch(
                        'allergens', Allergen.objects.only('name')),
                        'countries')
                # .distinct() jest już w filtrze, ale tutaj nie zaszkodzi
                .distinct())
    

class ListGlobalProducts(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated, IsProductOwner]
    pagination_class = CustomPagination
    
    filter_backends = [SmartHybridSearchFilter, OrderingFilter]

    ordering_fields = ['total_kcal', 'total_protein', 'total_fat', 'total_carbohydrates', 'display_salt']

    # Dodać filtr jeszcze na kraj wybrany przez użytkownika/kod pocztowy/miasto cokolwiek
    def get_queryset(self):
        return (Product.objects
                .filter(user__isnull=True)
                .with_nutrients()
                .select_related('category', 'packaging_type')
                .prefetch_related(
                    Prefetch(
                        'allergens', Allergen.objects.only('name')),
                        'countries')
                # .distinct() jest już w filtrze, ale tutaj nie zaszkodzi
                .distinct())
    

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all().with_nutrients()
    permission_classes = [IsAuthenticated, IsProductOwner]
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductCreateSerializer
    

class MyDishesListView(viewsets.ModelViewSet):
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DishSerializer
        if self.action == 'retrieve':
            return RetriveDishSerializer

    def get_queryset(self):
        return (Dish.objects
                .filter(user=self.request.user)
                .select_related('category', 'diet_type')
                .annotate(
                    total_kcal=Sum(F('ingredients__weight_in_g') * F('ingredients__product__kcal_1g'), distinct=True),
                    total_protein=Sum(F('ingredients__weight_in_g') * F('ingredients__product__protein_1g'), distinct=True),
                    total_fat=Sum(F('ingredients__weight_in_g') * F('ingredients__product__fat_1g'), distinct=True),
                    total_carbohydrates=Sum(F('ingredients__weight_in_g') * F('ingredients__product__carbohydrates_1g'), distinct=True),
                    display_salt=Sum(F('ingredients__weight_in_g') * F('ingredients__product__salt_1g'), distinct=True),
                    products_allergens = Coalesce(
                        ArrayAgg(
                            'ingredients__product__allergens__name', 
                            distinct=True,
                            filter=Q(ingredients__product__allergens__name__isnull=False)
                        ),
                        Value([], output_field=ArrayField(CharField()))
                    ))
                .prefetch_related(
                    Prefetch(
                        'additional_allergens',
                        queryset=Allergen.objects.filter(name__isnull=False).distinct()
                    )
                ))
                

class CreateMyDish(generics.CreateAPIView):
    serializer_class = DishCreateSerializer
    queryset = Dish.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UpdateMyDish(generics.UpdateAPIView):
    serializer_class = DishCreateSerializer
    permission_classes = [IsAuthenticated, IsProductOwner]
    queryset = Dish.objects.all()


class DestroyMyDish(generics.DestroyAPIView):
    serializer_class = DishCreateSerializer
    permission_classes = [IsAuthenticated, IsProductOwner]
    queryset = Dish.objects.all()


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