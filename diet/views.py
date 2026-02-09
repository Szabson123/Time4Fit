from django.shortcuts import render
from django.db.models import Prefetch

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from .serializers import ProductCategorySerializer, ProductCreateSerializer, ProductListSerializer, AllergenSerializer
from .models import Product, Allergen, ProductCategory


class CategoryHelper(generics.ListAPIView):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()


class AllergensHelper(generics.ListAPIView):
    serializer_class = AllergenSerializer

    def get_queryset(self):
        return Allergen.objects.filter(product__user=self.request.user).distinct('name').order_by('name')


class CustomPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 60


class CreateProductView(generics.CreateAPIView):
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]


class ListMyProductView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ['title', 'category__name', 'barcode', 'allergens__name']
    ordering_fields = ['kcal_1g', 'protein_1g', 'fat_1g', 'carbohydrates_1g', 'salt_1g']

    def get_queryset(self):
        return (Product.objects
                .filter(user=self.request.user)
                .select_related('category', 'packaging_type')
                .prefetch_related(
                    Prefetch(
                        'allergens', 
                        queryset=Allergen.objects.only('name')
                    )
                ))
    

