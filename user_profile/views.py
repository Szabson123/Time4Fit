from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count, Subquery, Q, Avg, DecimalField, Prefetch, ExpressionWrapper, F, IntegerField, Case, When, Value, BooleanField
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.validators import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from .serializers import TrainerListSerializer, PostSerializer, ProfileTrainerSerializer, CertyficationTrainerSerializer, TrainerFullProfileSerializer
from .models import TrainerPost, TrainerProfile, CertyficationTrainer, TrainerImages
from .permissions import OnlyOwnerOfProfileCanModify, OnlyOnwerOfTrainerProfile
from event.models import Event
from .utils import *

class TrainerPostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    queryset = TrainerPost.objects.all()
    permission_classes = [IsAuthenticated, OnlyOnwerOfTrainerProfile]

    def perform_create(self, serializer):
        trainer_profile = self.request.user.profile.trainerprofile
        serializer.save(trainer=trainer_profile)


class ProfileTrainerViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileTrainerSerializer
    queryset = TrainerProfile.objects.all()
    permission_classes = [IsAuthenticated, OnlyOwnerOfProfileCanModify]
    http_method_names = ["post", "put", "patch", "delete"]

    def perform_create(self, serializer):
        profile = self.request.user.profile
        if hasattr(profile, 'trainerprofile'):
            raise ValidationError({'error': 'You already have trainer profile', 'code': 'trainer_profile_already_exists'})
        
        serializer.save(profile=profile)


class CertyficationViewSet(viewsets.ModelViewSet):
    serializer_class = CertyficationTrainerSerializer
    queryset = CertyficationTrainer.objects.all()
    permission_classes = [IsAuthenticated, OnlyOnwerOfTrainerProfile]

    def perform_create(self, serializer):
        trainer_profile = self.request.user.profile.trainerprofile
        serializer.save(trainer=trainer_profile)


class TrainerFullProfileView(RetrieveAPIView):
    serializer_class = TrainerFullProfileSerializer
    permission_classes = [AllowAny]
    queryset = (
        TrainerProfile.objects
        .select_related('profile', 'profile__user')
        .annotate(
            event_past=Coalesce(Subquery(event_sq, output_field=IntegerField()), Value(0)),
            rate_avg=Subquery(avg_rate_sq, output_field=DecimalField()),
            followers_count=Coalesce(Subquery(followers_sq, output_field=IntegerField()), Value(0))
        )
        .prefetch_related(
            Prefetch(
                'posts',
                queryset=TrainerPost.objects.order_by('-date')[:5],
                to_attr='last_posts'
            ),
            Prefetch(
                'profile__user__events',
                queryset=Event.objects.filter(public_event=True)
                .select_related('additional_info')
                .annotate(
                    taken_spots=Count('eventparticipant'),
                    available_places=ExpressionWrapper(
                        F('additional_info__places_for_people_limit') - Count('eventparticipant'),
                        output_field=IntegerField()
                    ),
                    is_free=ExpressionWrapper(
                        Q(additional_info__price=0),
                        output_field=BooleanField()
                    )
                )
                # Pamiętać zadziała to tylko przy detail view nigdy przy liście
                .order_by('-date_time_event')[:3],
                to_attr='similar_events'
            )
        )
    )
    lookup_url_kwarg = 'trainer_id'


class TrainerProfilesListViewSet(ListAPIView):
    serializer_class = TrainerListSerializer
    permission_classes = [AllowAny]
    queryset = (
        TrainerProfile.objects
        .select_related('profile')
        .annotate(
            num_photos=Coalesce(Subquery(photos_sq, output_field=IntegerField()), Value(0)),
            avg_rate=Subquery(avg_rate_sq, output_field=DecimalField()),
            followers_count=Coalesce(Subquery(followers_sq, output_field=IntegerField()), Value(0))
        )
    )