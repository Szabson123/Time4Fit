from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from rest_framework import viewsets, response, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, CreateAPIView

from .serializers import EventSerializer, EventInvitationCreateSerializer, EventListSerializer, CategorySerializer, EventParticipantSerializer, EventInvitationSerializer
from .models import Event, Category, EventParticipant, EventInvitation


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if self.action == "list":
            return Event.objects.filter(public_event=True)
        
        if self.action == "retrieve":
            return Event.objects.filter(
                Q(public_event=True) | Q(eventparticipant__user=user)
            ).distinct()

        return Event.objects.filter(author=user)
    

class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class EventParticipantList(ListAPIView):
    serializer_class = EventParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author:
            return EventParticipant.objects.filter(event=event)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'treiner']).exists():
            return EventParticipant.objects.filter(event=event)

        raise Response({"error": "You dont have permissions", "code": "no_perm"}, status=status.HTTP_400_BAD_REQUEST)
    

class EventInvitationListView(ListAPIView):
    serializer_class = EventInvitationSerializer

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author:
            return EventInvitation.objects.filter(event=event)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'treiner']).exists():
            return EventInvitation.objects.filter(event=event)
        
        raise Response({"error": "You dont have permissions", "code": "no_perm"}, status=status.HTTP_400_BAD_REQUEST)
    

class EventInvitationCreateView(CreateAPIView):
    serializer_class = EventInvitationCreateSerializer

    def perform_create(self, serializer):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if event.author != self.request.user:
            raise Response({"error": "You dont have permissions", "code": "no_perm"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(created_by=self.request.user, event=event)

