from django.shortcuts import render
from django.db.models import Prefetch, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from .serializers import ProductCategorySerializer, ProductCreateSerializer, ProductListSerializer, AllergenSerializer
from .models import Product, Allergen, ProductCategory
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
                        'allergens',
                        Allergen.objects.only('name')
                    ))
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