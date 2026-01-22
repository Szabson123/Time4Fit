from django.db import models
from user.models import CentralUser
from django.core.validators import MinValueValidator, MaxValueValidator

Sex_choices = [
    ('male', 'Male'),
    ('female', 'Famale'),
    ('none', 'None'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(CentralUser, on_delete=models.CASCADE, related_name="profile")

    name = models.CharField(max_length=255, null=True, blank=True)
    surname = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    
    profile_description = models.TextField(null=True, blank=True)
    show_profile_public = models.BooleanField(default=False)

    birth_day = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=255, choices=Sex_choices, default='none')
    profile_picture = models.ImageField(null=True, blank=True, upload_to="profile_pictures/")


class TrainerProfile(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='trainerprofile')
    pick_specialization = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)
    specializations = models.CharField(max_length=1000, null=True, blank=True)
    business_email = models.EmailField(null=True, blank=True)
    phone_business = models.CharField(max_length=255, null=True, blank=True)
    img_profile = models.ImageField(upload_to='img_profile/', null=True, blank=True)


class TrainerRate(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='trainerrate')
    user = models.ForeignKey(CentralUser, on_delete=models.CASCADE, related_name='trainerrate')
    rate = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    time_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trainer', 'user')


class TrainerObservation(models.Model):
    follower = models.ForeignKey(CentralUser, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')


class CertyficationTrainer(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='certyficates')
    title = models.CharField(max_length=255)
    issued_by = models.CharField(max_length=255, null=True, blank=True)
    identyficatior = models.CharField(max_length=50, null=True, blank=True)
    issued_date = models.DateField()
    additional_fields = models.CharField(max_length=500, null=True, blank=True)


class CertificationFile(models.Model):
    certyficat = models.ForeignKey(CertyficationTrainer, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='cert_photos/')


class TrainerPost(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name='posts')
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=2000)
    likes = models.PositiveIntegerField(default=0)


class PostImage(models.Model):
    post = models.ForeignKey(TrainerPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='post_photos/')
    