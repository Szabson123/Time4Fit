from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateProductView, ListMyProductView


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='create-product'),
    path('list-my-product/', ListMyProductView.as_view(), name='list-my-product')
]