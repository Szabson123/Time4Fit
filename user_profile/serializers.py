from .models import PostImage, TrainerPost, TrainerProfile, CertificationFile, CertyficationTrainer, UserProfile
from rest_framework import serializers
from django.db import transaction
from rest_framework.validators import ValidationError
from event.models import Event, EventAdditionalInfo

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'name', 'surname']


class ProfileTrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerProfile
        fields = ['id', 'description', 'specializations', 'business_email', 'phone_business', 'img_profile', 'pick_specialization']


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image']


class PostSerializer(serializers.ModelSerializer):
    images = PostImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(child=serializers.ImageField(allow_empty_file=False, use_url=False),write_only=True)

    class Meta:
        model = TrainerPost
        fields = ["id", "description", "likes", "images", "uploaded_images", "date"]
        read_only_fields = ['likes', "date"]

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images")

        post = TrainerPost.objects.create(**validated_data)
        for image in uploaded_images:
            PostImage.objects.create(post=post, image=image)
        
        return post

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if uploaded_images is not None:
            instance.photos.all().delete()
            for image in uploaded_images:
                PostImage.objects.create(post=instance, image=image)

        return instance


class CertificationFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationFile
        fields = ['id', 'image']


class CertyficationTrainerSerializer(serializers.ModelSerializer):
    images = CertificationFileSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(child=serializers.ImageField(allow_empty_file=False, use_url=False),write_only=True)

    class Meta:
        model = CertyficationTrainer
        fields = ['id', 'title', 'issued_by', 'identyficatior', 'issued_date', 'additional_fields', 'images', 'uploaded_images']

    def create(self, validated_data):
        uploaded_images_data = validated_data.pop('uploaded_images', [])
        
        if uploaded_images_data is not None and len(uploaded_images_data) > 4:
            raise ValidationError({"error": "Max 4 images allowed.", "code": "uploaded_image_limit_exceeded"})
        
        cert = CertyficationTrainer.objects.create(**validated_data)

        for img in uploaded_images_data:
            CertificationFile.objects.create(certyficat=cert, image=img)

        return cert
    
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', None)

        if uploaded_images is not None and len(uploaded_images) > 4:
            raise ValidationError({"error": "Max 4 images allowed.", "code": "uploaded_image_limit_exceeded"})

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if uploaded_images is not None:
                instance.images.all().delete()

                for img in uploaded_images:
                    CertificationFile.objects.create(certyficat=instance, image=img)

        return instance


class AdditionalEventInfoToPrfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAdditionalInfo
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit']

class EventTrainerSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(read_only=True, source='category.name')
    additional_info = AdditionalEventInfoToPrfileSerializer(many=False, read_only=True)
    class Meta:
        model = Event
        fields = ['id', 'category_name', 'date_time_event', 'city', 'street', 'street_number', 'flat_number', 'additional_info']


class TrainerFullProfileSerializer(serializers.Serializer):
    description = serializers.CharField()
    specializations = serializers.CharField()
    phone_business = serializers.CharField()
    business_email = serializers.EmailField()
    img_profile = serializers.ImageField()
    pick_specialization = serializers.CharField()
    profile = UserProfileSerializer()
    event_past = serializers.IntegerField()
    rate_avg = serializers.DecimalField(decimal_places=1, max_digits=5)
    followers_count = serializers.IntegerField()
    certyficates = CertyficationTrainerSerializer(many=True, read_only=True)
    posts = PostSerializer(many=True, read_only=True, source='last_posts')
    events = EventTrainerSerializer(many=True, read_only=True, source='profile.user.similar_events')

