from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from rest_framework import viewsets, status, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, CreateAPIView, GenericAPIView
from rest_framework.exceptions import PermissionDenied

from .serializers import( EventSerializer, EventInvitationCreateSerializer, EventListSerializer, CodeSerializer,
                          CategorySerializer, EventParticipantSerializer, EventInvitationSerializer, EventInvSerializer, NoneSerializer,
                          ChangeRoleSerializer)

from .models import Event, Category, EventParticipant, EventInvitation, PARTICIPANT_ROLES
from .permissions import IsEventAuthor



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
                Q(public_event=True) | Q(eventparticipant__user=user) | Q(author=user)
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

        raise PermissionDenied(detail="You don't have permissions")
    

class ChangeUserRankInEvent(GenericAPIView):
    serializer_class = ChangeRoleSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        event_id = kwargs.get('event_id')
        participant_id = kwargs.get('participant_id')
        event = get_object_or_404(Event, pk=event_id)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'treiner']).exists():
            
            participant = get_object_or_404(EventParticipant, pk=participant_id, event=event)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            new_role = serializer.validated_data['new_role']

            if new_role == participant.role:
                return Response({"detail": "Already has this role."}, status=status.HTTP_200_OK)
            
            VALID_ROLES = [r[0] for r in PARTICIPANT_ROLES]

            if new_role not in VALID_ROLES:
                return Response({"detail": "This role doesn't exist."}, status=status.HTTP_400_BAD_REQUEST)
            
            participant.role = new_role
            participant.save(update_fields=["role"])

            return Response({
                "status": "changed role",
                "participant": EventParticipantSerializer(participant).data
            })
        
        else:
            raise PermissionDenied(detail="You don't have permissions")


class EventInvitationViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EventInvitationCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return EventInvitationSerializer
        elif self.action == 'deactivate' or self.action == 'activate':
            return NoneSerializer
        
        return EventInvitationCreateSerializer

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author:
            return EventInvitation.objects.select_related("event").filter(event=event)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'trainer']).exists():
            return EventInvitation.objects.select_related("event").filter(event=event)
        
        raise PermissionDenied(detail="You don't have permissions")

    def perform_create(self, serializer):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if event.author != self.request.user:
            raise PermissionDenied(detail="You don't have permissions to invite users to this event.")
        
        serializer.save(created_by=self.request.user, event=event)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEventAuthor])
    def deactivate(self, request, pk=None, *args, **kwargs):
        invitation = self.get_object()
        invitation.is_active = False
        invitation.save(update_fields=["is_active"])

        return Response(
            {"status": "deactivated", "invitation_id": invitation.id}
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEventAuthor])
    def activate(self, request, pk=None, *args, **kwargs):
        invitation = self.get_object()
        invitation.is_active = True
        invitation.save(update_fields=["is_active"])

        return Response(
            {"status": "activate", "invitation_id": invitation.id}
        )


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

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        code = ser.validated_data['code']

        inv = EventInvitation.objects.select_for_update().filter(code=code).first()
        if not inv or not inv.is_valid_code:
            return Response({"detail": "Invalid or expired invitation"}, status=400)

        event = inv.event
        # limit miejsc
        
        add = getattr(event, 'additional_info', None)
        if add and add.places_for_people_limit:
            current = EventParticipant.objects.select_for_update().filter(event=event).count()
            if current >= add.places_for_people_limit:
                return Response({"detail": "No seats available"}, status=409)

        obj, created = EventParticipant.objects.get_or_create(
            user=request.user, event=event, defaults={'role': 'participant'}
        )

        if inv.is_one_use:
            if inv.is_used:
                return Response({"detail": "Invitation already used"}, status=409)
            inv.is_used = True
            inv.save(update_fields=["is_used"])

        return Response({"status": "success"}, status=200)