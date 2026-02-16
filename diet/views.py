from django.shortcuts import render
from django.db.models import Prefetch, F, ExpressionWrapper, DecimalField, Sum, CharField, Q, Value
from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, viewsets, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from .serializers import ProductCategorySerializer, DishSerializer, ProductCreateSerializer, ProductListSerializer, AllergenSerializer, DishCreateSerializer, RetriveDishSerializer
from .models import Product, Allergen, ProductCategory, Dish
from .filters import SmartHybridSearchFilter
from .permissions import IsProductOwner


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
    

class MyDishesListView(viewsets.ReadOnlyModelViewSet):
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DishSerializer
        if self.action == 'retrieve':
            return RetriveDishSerializer

    def get_queryset(self):
        return (Dish.objects
                .filter(author=self.request.user)
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
        serializer.save(author=self.request.user)

