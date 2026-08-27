from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyMealCalendarDetailView,
    AddProductToMealView,
    CreateCustomMealView,
    ProductListView,
    ProductDetailView,
    ProductDetailByBarcodeView,
)


urlpatterns = [
    path('daily-meals/', DailyMealCalendarDetailView.as_view(), name='daily-meals'),
    path('add-product/', AddProductToMealView.as_view(), name='add-product-to-meal'),
    path('add-meal/', CreateCustomMealView.as_view(), name='add-custom-meal'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/barcode/<str:barcode>/', ProductDetailByBarcodeView.as_view(), name='product-detail-barcode'),
]
