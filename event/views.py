from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import viewsets, status, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView, CreateAPIView, GenericAPIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.throttling import UserRateThrottle

from .serializers import( EventSerializer, EventInvitationCreateSerializer, EventListSerializer, CodeSerializer,
                          CategorySerializer, EventParticipantSerializer, EventInvitationSerializer, EventInvSerializer, NoneSerializer,
                          ChangeRoleSerializer, EventMapSerializer)

from .models import Event, Category, EventParticipant, EventInvitation, PARTICIPANT_ROLES
from .permissions import IsEventAuthor, IsAuthorOrReadOnly
from .filters import EventListFilter


class CustomPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 60

class TenPerMinuteThrottle(UserRateThrottle):
    rate = '10/min'


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    pagination_class = CustomPagination
    filterset_class = EventListFilter

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        base_qs = Event.objects.select_related('category', 'additional_info').prefetch_related('eventparticipant__user__profile').order_by('date_time_event')

        filters = Q(public_event=True)
        if user.is_authenticated:
            filters |= Q(author=user)
            filters |= Q(eventparticipant__user=user)

        if self.action == "list":
            return (
                base_qs
                .filter(filters, date_time_event__gte=timezone.now())
                .annotate(event_participant_count=Count('eventparticipant'))
            )

        if self.action == "retrieve":
            return (
                base_qs
                .filter(filters,date_time_event__gte=timezone.now())
                .annotate(event_participant_count=Count('eventparticipant'))
                .distinct()
            )

        return base_qs.filter(author=user)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny], serializer_class=EventMapSerializer)
    def events_on_map(self, request, *args, **kwargs):
        queryset = Event.objects.filter(public_event=True, date_time_event__gte=timezone.now())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], serializer_class=EventSerializer, throttle_classes = [TenPerMinuteThrottle], url_path=r'by-code/(?P<access_code>[^/.]+)')
    def get_event_with_code(self, request, *args, **kwargs):
        access_code = self.kwargs.get('access_code')
        try:
            event = Event.objects.filter(
                eventinvitation__code=access_code,
                eventinvitation__is_active=True,
                eventinvitation__is_used=False,
                date_time_event__gte=timezone.now()
            ).latest('date_time_event')
            
        except Event.DoesNotExist:
            return Response({"error": "Event didnt found", "code": "event_does_not_exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(event, many=False)
        return Response(serializer.data)


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated]


class EventParticipantList(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EventParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author or EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'trainer']).exists():
            return EventParticipant.objects.select_related('event').filter(event=event)

        raise PermissionDenied(detail="You don't have permissions")
    
    @action(detail=True, permission_classes=[IsEventAuthor], methods=['post'])
    def delete_user_from_participant_list(self, request, *args, **kwargs):
        participant = self.get_object()
        participant.delete()
        return Response({"detail": "User has been removed from list"}, status=status.HTTP_204_NO_CONTENT)
    

class ChangeUserRankInEvent(GenericAPIView):
    serializer_class = ChangeRoleSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        event_id = kwargs.get('event_id')
        participant_id = kwargs.get('participant_id')
        event = get_object_or_404(Event, pk=event_id)

        if EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'trainer']).exists() or request.user == event.author:
            
            participant = get_object_or_404(EventParticipant, pk=participant_id, event=event)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            new_role = serializer.validated_data['new_role']

            if new_role == participant.role:
                return Response({"error": "Already has this role", "code": "role_aleardy_assigned"}, status=status.HTTP_200_OK)
            
            VALID_ROLES = [r[0] for r in PARTICIPANT_ROLES]

            if new_role not in VALID_ROLES:
                return Response({"error": "This role doesn't exist", "code": "role_didnt_found"}, status=status.HTTP_400_BAD_REQUEST)
            
            participant.role = new_role
            participant.save(update_fields=["role"])

            return Response({
                "status": "changed role",
                "participant": EventParticipantSerializer(participant).data
            })
        
        else:
            raise PermissionDenied({"error": "You don't have permissions to invite users to this event", "code": "no_permissions"})


class EventInvitationViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EventInvitationCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return EventInvitationSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if user == event.author or EventParticipant.objects.filter(event=event, user=user, role__in=['admin', 'trainer']).exists():
            return EventInvitation.objects.select_related('event').filter(event=event)

        raise PermissionDenied({"error": "You don't have permissions to invite users to this event", "code": "no_permissions"})

    def perform_create(self, serializer):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, pk=event_id)

        if event.author != self.request.user:
            raise PermissionDenied({"error": "You don't have permissions to invite users to this event", "code": "no_permissions"})
        
        serializer.save(created_by=self.request.user, event=event)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEventAuthor], serializer_class=NoneSerializer)
    def deactivate(self, request, pk=None, *args, **kwargs):
        invitation = self.get_object()
        invitation.is_active = False
        invitation.save(update_fields=["is_active"])

        return Response(
            {"status": "deactivated", "invitation_id": invitation.id}
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEventAuthor], serializer_class=NoneSerializer)
    def activate(self, request, pk=None, *args, **kwargs):
        invitation = self.get_object()
        invitation.is_active = True
        invitation.save(update_fields=["is_active"])

        return Response(
            {"status": "activate", "invitation_id": invitation.id}
        )

class InvGetIntoEvent(GenericAPIView):
    serializer_class = CodeSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        code = ser.validated_data['code']

        inv = EventInvitation.objects.select_for_update().filter(code=code).first()
        if not inv or not inv.is_valid:
            return Response({"error": "Invalid or expired invitation", "code": "invalid_invitation_code"}, status=status.HTTP_400_BAD_REQUEST)

        event = inv.event
        # limit miejsc

        add = getattr(event, 'additional_info', None)
        if add and add.places_for_people_limit:
            current = EventParticipant.objects.select_for_update().filter(event=event).count()
            if current >= add.places_for_people_limit:
                return Response({"detail": "No seats available"}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = EventParticipant.objects.get_or_create(
            user=request.user, event=event, defaults={'role': 'participant'}
        )

        if inv.is_one_use:
            if inv.is_used:
                return Response({"detail": "Invitation already used"}, status=status.HTTP_400_BAD_REQUEST)
            inv.is_used = True
            inv.save(update_fields=["is_used"])

        return Response({"status": "success"}, status=status.HTTP_200_OK)