from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, CategoryListView, EventParticipantList, EventInvitationViewSet, InvGetInfoOfEvent, InvGetIntoEvent


router = DefaultRouter()
router.register(r'events', EventViewSet, basename='events')
router.register(r'events/(?P<event_id>\d+)/invitations', EventInvitationViewSet, basename='event-inv')

urlpatterns = [
    path('', include(router.urls)),
    path('category-list/', CategoryListView.as_view(), name='category-list'),
    path('<int:event_id>/event-participant-list/', EventParticipantList.as_view(), name='event-participant-list'),

    path('<str:inv_code>/event-inv/', InvGetInfoOfEvent.as_view(), name='event-invitation'),
    path('event-inv-join/', InvGetIntoEvent.as_view(), name='event-invitation-join')
]