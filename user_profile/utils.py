from django.db.models import OuterRef, Avg, Count
from .models import TrainerImages, TrainerObservation, TrainerRate
from event.models import Event
from django.utils import timezone

photos_sq = (
    TrainerImages.objects
    .filter(collection__trainer=OuterRef('pk'))
    .values('collection__trainer')
    .annotate(cnt=Count('id'))
    .values('cnt')
)

followers_sq = (
    TrainerObservation.objects
    .filter(following=OuterRef('pk'))
    .values('following')
    .annotate(cnt=Count('id'))
    .values('cnt')
)

avg_rate_sq = (
    TrainerRate.objects
    .filter(trainer=OuterRef('pk'))
    .values('trainer')
    .annotate(avg=Avg('rate'))
    .values('avg')
)

event_sq = (
    Event.objects
    .filter(author__profile__trainerprofile=OuterRef('pk'), date_time_event__lt=timezone.now())
    .values('author__profile__trainerprofile')
    .annotate(cnt=Count('id'))
    .values('cnt')
)