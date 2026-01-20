from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, CategoryListView, EventParticipantList, EventInvitationViewSet, InvGetIntoEvent, ChangeUserRankInEvent


router = DefaultRouter()
router.register(r'events', EventViewSet, basename='events')
router.register(r'events/(?P<event_id>\d+)/invitations', EventInvitationViewSet, basename='event-inv')
router.register(r'(?P<event_id>\d+)/event-participant-list', EventParticipantList, basename='event-participant-list')

urlpatterns = [
    path('', include(router.urls)),
    path('<int:event_id>/change-role/<int:participant_id>/', ChangeUserRankInEvent.as_view(), name='change-part-role'),
    path('category-list/', CategoryListView.as_view(), name='category-list'),
    path('event-inv-join/', InvGetIntoEvent.as_view(), name='event-invitation-join')
]