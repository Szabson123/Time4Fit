from django.shortcuts import render
from django.db.models import Prefetch

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter

from .serializers import ProductCategorySerializer, ProductCreateSerializer, ProductListSerializer
from .models import Product, Allergen


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
    filter_backends = [SearchFilter]

    search_fields = ['title', 'category__name', 'barcode', 'allergens__name']

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