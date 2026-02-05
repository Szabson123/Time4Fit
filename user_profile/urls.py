from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (TrainerPostViewSet, ProfileTrainerViewSet, TrainerFullProfileView, CertyficationViewSet, TrainerProfilesListViewSet,
                    GiveObservationView, RevokeObservationView, PhotosCollectionViewSet)


router = DefaultRouter()
router.register(r'posts', TrainerPostViewSet, basename='events')
router.register(r'trainer-profiles', ProfileTrainerViewSet, basename='trainer-profiles')
router.register(r'trainer-certyficates', CertyficationViewSet, basename='certyficates')
router.register(r'trainer-collections', CertyficationViewSet, basename='collections')

urlpatterns = [
    path('', include(router.urls)),
    path('trainer-full-profile/<int:trainer_id>/', TrainerFullProfileView.as_view(), name='trainer-full-profile'),
    path('trainers-list/', TrainerProfilesListViewSet.as_view(), name='trainer-list'),
    path('give-obs/<int:trainer_id>/', GiveObservationView.as_view(), name='give-obs'),
    path('revoke-obs/<int:trainer_id>/', RevokeObservationView.as_view(), name='revoke-obs')
]
