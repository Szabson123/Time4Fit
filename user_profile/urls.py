from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainerPostViewSet


router = DefaultRouter()
router.register(r'posts', TrainerPostViewSet, basename='events')

urlpatterns = [
    path('', include(router.urls)),
]
