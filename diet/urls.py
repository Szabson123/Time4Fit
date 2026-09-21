from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyMealCalendarDetailView,
    AddProductToMealView,
    CreateCustomMealView,
    ProductListView,
    ProductCreateView,
    ProductDetailView,
    ProductDetailByBarcodeView,
    DailyWaterIntakeView,
    QuickAddMealItemView,
    DailyUserMacrosView,
)


urlpatterns = [
    path('daily-meals/', DailyMealCalendarDetailView.as_view(), name='daily-meals'),
    path('daily-user-macros/', DailyUserMacrosView.as_view(), name='daily-user-macros'),
    path('dayly-user-macros/', DailyUserMacrosView.as_view(), name='dayly-user-macros'),
    path('add-product/', AddProductToMealView.as_view(), name='add-product-to-meal'),
    path('quick-add/', QuickAddMealItemView.as_view(), name='quick-add-meal-item'),
    path('add-meal/', CreateCustomMealView.as_view(), name='add-custom-meal'),
    path('water/', DailyWaterIntakeView.as_view(), name='daily-water'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/barcode/<str:barcode>/', ProductDetailByBarcodeView.as_view(), name='product-detail-barcode'),
]

