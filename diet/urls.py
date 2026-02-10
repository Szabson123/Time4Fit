from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateProductView, ListMyProductView, CategoryHelper, AllergensHelper, ProductDetailView


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='create-product'),
    path('list-my-product/', ListMyProductView.as_view(), name='list-my-product'),
    path('category-helper/', CategoryHelper.as_view(), name='category-helper'),
    path('allergens-helper/', AllergensHelper.as_view(), name='alleregens-helper'),
    path('my-products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
]