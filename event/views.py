from django.shortcuts import render
from rest_framework import viewsets, response, status
from rest_framework.response import Response

from .serializers import EventSerializer
from .models import Event


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()
