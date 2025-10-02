from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, CategoryListView


router = DefaultRouter()
router.register(r'events', EventViewSet, basename='events')

urlpatterns = [
    path('', include(router.urls)),
    path('category-list/', CategoryListView.as_view(), name='category-lsit')
]