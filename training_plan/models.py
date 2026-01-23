from django.db import models
from user.models import CentralUser


class SystemExercise(models.Model):
    name = models.CharField(max_length=255)

class BodyPartsAndTags(models.Model):
    name = models.CharField
    sys_excercise = models.ForeignKey(SystemExercise, on_delete=models.CASCADE, related_name='tags')


class TrainingPLan(models.Model):
    owner = models.ForeignKey(CentralUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    intensity = models.CharField(max_length=255, null=True, blank=True)
    advanced_level = models.CharField(max_length=255, null=True, blank=True)
    priority = models.CharField(max_length=255, null=True, blank=True)
    duration = models.PositiveIntegerField()


class Exercise(models.Model):
    training_plan = models.ForeignKey(TrainingPLan, on_delete=models.CASCADE, related_name='exercises')
    what_train = models.CharField(max_length=255) #Body part or Kardio or custom name
    name = models.CharField(max_length=255)
