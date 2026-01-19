from django.shortcuts import render
from .serializers import PostSerializer, ProfileTrainerSerializer, CertyficationTrainerSerializer
from .models import TrainerPost, TrainerProfile, CertyficationTrainer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.validators import ValidationError
from .permissions import OnlyOwnerOfProfileCanModify, OnlyOnwerOfTrainerProfile

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