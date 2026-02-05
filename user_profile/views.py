from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Count, Subquery, Q, Avg, DecimalField, Prefetch, ExpressionWrapper, F, IntegerField, Case, When, Value, BooleanField, ImageField
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.validators import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from .serializers import TrainerListSerializer, PostSerializer, ProfileTrainerSerializer, CertyficationTrainerSerializer, TrainerFullProfileSerializer, PhotosCollectionSerializer
from .models import TrainerPost, TrainerProfile, CertyficationTrainer, TrainerImages, PhotosCollection
from .permissions import OnlyOwnerOfProfileCanModify, OnlyOnwerOfTrainerProfile
from event.models import Event
from .utils import *
from event.serializers import NoneSerializer


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


class GiveObservationView(GenericAPIView):
    serializer_class = NoneSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        trainer_id = self.kwargs.get('trainer_id')
        user = self.request.user
        trainer = get_object_or_404(TrainerProfile, pk=trainer_id)

        obj, created = TrainerObservation.objects.get_or_create(follower=user, following=trainer)

        if not created:
            return Response({"error": "You already have observation", "code": "already_have_observation"},status=status.HTTP_409_CONFLICT)
        
        return Response({"id": obj.id}, status=status.HTTP_201_CREATED)
    

class RevokeObservationView(GenericAPIView):
    serializer_class = NoneSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        trainer_id = self.kwargs.get('trainer_id')
        user = self.request.user
        trainer = get_object_or_404(TrainerProfile, pk=trainer_id)

        deleted_count, _ = TrainerObservation.objects.filter(follower=user, following=trainer).delete()

        if deleted_count == 0:
            return Response({"error": "You are not observing this trainer", "code": "have_not_observation"},status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"success": "Observation revoked", "code": "obs_revoke_success"}, status=status.HTTP_200_OK)


class PhotosCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = PhotosCollectionSerializer

    def get_queryset(self):
        latest_photo_sq = TrainerImages.objects.filter(
            photoscollections=OuterRef('pk')
        ).order_by('-created_at').values('images')[:1]

        qs = PhotosCollection.objects.annotate(
            img_count=Count('images', distinct=True),
            first_img=Subquery(latest_photo_sq)
        )

        trainer_id_param = self.request.query_params.get('trainer_id')

        if trainer_id_param:
            return qs.filter(trainer_id=trainer_id_param)

        user = self.request.user
        if user.is_authenticated and hasattr(user, 'profile'):
            return qs.filter(trainer=user.profile.trainerprofile)

        raise ValidationError(
            {"error": "You need to pass trainer_id query param.", "code": "no_trainer_id"}
        )

    def perform_create(self, serializer):
        trainer = self.request.user.profile.trainerprofile
        serializer.save(trainer=trainer)


