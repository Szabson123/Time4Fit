from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CreateProductView, ListMyProductView, CategoryHelper, AllergensHelper,
                    ProductDetailView, MyDishesListView, CreateMyDish, ListGlobalProducts, DestroyMyDish, UpdateMyDish)


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='create-product'),

    path('list-my-product/', ListMyProductView.as_view(), name='list-my-product'),
    path('list-global-product/', ListGlobalProducts.as_view(), name='list-my-product'),

    path('category-helper/', CategoryHelper.as_view(), name='category-helper'),
    path('allergens-helper/', AllergensHelper.as_view(), name='alleregens-helper'),
    path('my-products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),

    path('my-dishes/', MyDishesListView.as_view({'get': 'list'}), name='my-dishes'),
    path('my-dishes/<int:pk>/', MyDishesListView.as_view({'get': 'retrieve'}), name='my-dishes'),

    path('create-dish/', CreateMyDish.as_view(), name='create-product'),
    path('update-dish/<int:pk>/', UpdateMyDish.as_view(), name='update-product'),
    path('delete-dish/<int:pk>/', DestroyMyDish.as_view(), name='delete-product'),

]