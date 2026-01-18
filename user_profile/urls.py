from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainerPostViewSet, ProfileTrainerViewSet


router = DefaultRouter()
router.register(r'posts', TrainerPostViewSet, basename='events')
router.register(r'trainer-profiles', ProfileTrainerViewSet, basename='trainer-profiles')

urlpatterns = [
    path('', include(router.urls)),
]
