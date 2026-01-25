from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg, Prefetch, ExpressionWrapper, F, IntegerField
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.validators import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import PostSerializer, ProfileTrainerSerializer, CertyficationTrainerSerializer, TrainerFullProfileSerializer
from .models import TrainerPost, TrainerProfile, CertyficationTrainer
from .permissions import OnlyOwnerOfProfileCanModify, OnlyOnwerOfTrainerProfile
from event.models import Event


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


class TrainerFullProfileView(GenericAPIView):
    serializer_class = TrainerFullProfileSerializer
    permission_classes = [AllowAny]
    queryset = (
        TrainerProfile.objects
        .select_related('profile', 'profile__user')
        .annotate(
            event_past=Count(
                'profile__user__events',
                filter=Q(profile__user__events__date_time_event__lt=timezone.now()),
                distinct=True,
            ),
            rate_avg=Avg('trainerrate__rate'),
            followers_count=Count('followers', distinct=True),
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
                    )
                )
                .order_by('-date_time_event')[:3],
                to_attr='similar_events'
            )
        )
    )
    lookup_url_kwarg = 'trainer_id'

    def get(self, request, *args, **kwargs):
        trainer = self.get_object()
        serializer = self.get_serializer(trainer)
        return Response(serializer.data)
