from .models import PostImage, TrainerPost, TrainerProfile
from rest_framework import serializers


class ProfileTrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainerProfile
        fields = ['id', 'description', 'specializations', 'profile']
        read_only_fields = ['profile']


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image']


class PostSerializer(serializers.ModelSerializer):
    images = PostImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(child=serializers.ImageField(allow_empty_file=False, use_url=False),write_only=True)

    class Meta:
        model = TrainerPost
        fields = ["id", "description", "likes", "images", "uploaded_images"]
        read_only_fields = ['likes']

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images")

        post = TrainerPost.objects.create(**validated_data)
        for image in uploaded_images:
            PostImage.objects.create(post=post, image=image)
        
        return post

    def update(self, instance, validated_data):
        images_data = validated_data.pop("images", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data:
            instance.photos.all().delete()
            for images in images_data:
                PostImage.objects.create(post=instance, **images)

        return instance

