from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, CategoryListView, EventParticipantList, EventInvitationListView, EventInvitationCreateView, InvGetInfoOfEvent, InvGetIntoEvent


router = DefaultRouter()
router.register(r'events', EventViewSet, basename='events')

urlpatterns = [
    path('', include(router.urls)),
    path('category-list/', CategoryListView.as_view(), name='category-list'),
    path('<int:event_id>/event-participant-list/', EventParticipantList.as_view(), name='event-participant-list'),
    path('<int:event_id>/event-invitation-list/', EventInvitationListView.as_view(), name='event-invitation-list'),
    path('<int:event_id>/event-invitation-create/', EventInvitationCreateView.as_view(), name='event-invitation-list'),

    path('<str:inv_code>/event-inv/', InvGetInfoOfEvent.as_view(), name='event-invitation'),
    path('event-inv-join/', InvGetIntoEvent.as_view(), name='event-invitation-join')
]