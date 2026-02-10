from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateProductView, ListMyProductView, CategoryHelper, AllergensHelper, RetrieveMyProductView, UpdateMyProductView, DeleteMyProductView


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='create-product'),
    path('list-my-product/', ListMyProductView.as_view(), name='list-my-product'),
    path('category-helper/', CategoryHelper.as_view(), name='category-helper'),
    path('allergens-helper/', AllergensHelper.as_view(), name='alleregens-helper'),
    path('my-product-details/<int:id>/', RetrieveMyProductView.as_view(), name='my-product-details'),
    path('my-product-update/<int:id>/', UpdateMyProductView.as_view(), name='my-product-update'),
    path('my-product-delete/<int:id>/', DeleteMyProductView.as_view(), name='my-product-delete'),
]