from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateProductView


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='create-product')
]