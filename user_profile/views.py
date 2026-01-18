from django.shortcuts import render
from .serializers import PostSerializer, ProfileTrainerSerializer
from .models import TrainerPost, TrainerProfile
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny


class TrainerPostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    queryset = TrainerPost.objects.all()
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        trainer_profile = self.request.user.profile.trainerprofile
        serializer.save(trainer=trainer_profile)


class ProfileTrainerViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileTrainerSerializer
    queryset = TrainerProfile.objects.all()

    def perform_create(self, serializer):
        profile = self.request.user.profile
        serializer.save(profile=profile)