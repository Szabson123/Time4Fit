from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, response, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from .serializers import EventSerializer, CategorySerializer, EventParticipantSerializer
from .models import Event, Category, EventParticipant


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


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