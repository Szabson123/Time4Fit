from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, response, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, CreateAPIView, GenericAPIView
from rest_framework.exceptions import PermissionDenied

from .serializers import( EventSerializer, EventInvitationCreateSerializer, EventListSerializer, CodeSerializer,
                          CategorySerializer, EventParticipantSerializer, EventInvitationSerializer, EventInvSerializer)

from .models import Event, Category, EventParticipant, EventInvitation


class CustomPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 100


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if self.action == "list":
            return Event.objects.filter(public_event=True, date_time_event__gte = timezone.now())
        
        if self.action == "retrieve":
            return Event.objects.filter(
                Q(public_event=True) | Q(eventparticipant__user=user)
            ).distinct()

        return Event.objects.filter(author=user)
    

class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated]


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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author:
            return EventInvitation.objects.select_related("event").filter(event=event)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'treiner']).exists():
            return EventInvitation.objects.select_related("event").filter(event=event)
        
        raise PermissionDenied(detail="You don't have permissions")
    

class EventInvitationCreateView(CreateAPIView):
    serializer_class = EventInvitationCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if event.author != self.request.user:
            raise Response({"error": "You dont have permissions", "code": "no_perm"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(created_by=self.request.user, event=event)


class InvGetInfoOfEvent(GenericAPIView):
    serializer_class = EventInvSerializer
    def get(self, request, *args, **kwargs):
        code = self.kwargs.get('inv_code')

        inv = EventInvitation.objects.filter(code=code).first()

        if not inv or not inv.is_valid_code:
            return Response({"error": "Invalid or expired invitation"}, status=400)


        serializer = self.get_serializer(inv.event)
        return Response(serializer.data)
    

class InvGetIntoEvent(GenericAPIView):
    serializer_class = CodeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        user = self.request.user
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        inv = EventInvitation.objects.filter(code=code).first()

        if inv.is_one_use:
            inv.is_used = True
            inv.save(update_fields=["is_used"])
        
        EventParticipant.objects.get_or_create(
            user=user,
            event=inv.event,
            role='participant',
        )

        return Response("success", status=status.HTTP_200_OK)