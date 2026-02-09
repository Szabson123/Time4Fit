from django.shortcuts import render

from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status

from .serializers import ProductCategorySerializer, ProductCreateSerializer
from .models import Product


class CreateProductView(generics.CreateAPIView):
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]

