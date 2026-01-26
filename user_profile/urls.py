from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainerPostViewSet, ProfileTrainerViewSet, TrainerFullProfileView, CertyficationViewSet, TrainerProfilesListViewSet


router = DefaultRouter()
router.register(r'posts', TrainerPostViewSet, basename='events')
router.register(r'trainer-profiles', ProfileTrainerViewSet, basename='trainer-profiles')
router.register(r'trainer-certyficates', CertyficationViewSet, basename='certyficates')

urlpatterns = [
    path('', include(router.urls)),
    path('trainer-full-profile/<int:trainer_id>/', TrainerFullProfileView.as_view(), name='trainer-full-profile'),
    path('trainers-list/', TrainerProfilesListViewSet.as_view(), name='trainer-list'),
]
