from .models import Event, EventAdditionalInfo, SpecialGuests, Category, EventParticipant
from rest_framework import serializers
from user_profile.models import UserProfile
from user.models import CentralUser

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class SpecialGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialGuests
        fields = ['id', 'name', 'surname']


class EventAdditionalInfoSerializer(serializers.ModelSerializer):
    special_guests = SpecialGuestSerializer(many=True, required=False)
    class Meta:

        model = EventAdditionalInfo
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'participant_list_show', 'public_event', 'free', 'price', 'payment_in_app', 'special_guests']

    def create(self, validated_data):
        guest_data = validated_data.pop("special_guests", [])
        add_info = EventAdditionalInfo.objects.create(**validated_data)

        for guest in guest_data:
            SpecialGuests.objects.create(add_info=add_info, **guest)
        
        return add_info
    
    def update(self, instance, validated_data):
        guest_data = validated_data.pop("special_guests", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if guest_data:
            instance.special_guests.all().delete()
            for guest in guest_data:
                SpecialGuests.objects.create(add_info=instance, **guest)

        return instance


class EventSerializer(serializers.ModelSerializer):
    additional_info = EventAdditionalInfoSerializer()

    class Meta:
        model = Event
        read_only_fields = ['unique_id', 'author']
        fields = ['id', 'unique_id', 'author', 'title', 'category', 'short_desc', 'long_desc', 'date_time_event', 'duration_min',
                'latitude', 'longitude',
                'country', 'city', 'street', 'street_number', 'flat_number', 'zip_code',
                'additional_info']
        
    def create(self, validated_data):
        additional_info_data = validated_data.pop("additional_info")

        event = Event.objects.create(**validated_data)
        EventAdditionalInfoSerializer().create({
            **additional_info_data,
            "event": event
        })

        return event
    
    def update(self, instance, validated_data):
        additional_info_data = validated_data.pop("additional_info", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if additional_info_data is not None:
            info_serializer = EventAdditionalInfoSerializer(
                instance=instance.additional_info,
                data=additional_info_data,
                partial=True
            )

            info_serializer.is_valid(raise_exception=True)
            info_serializer.save()

        return instance
    

class ProfileEventParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['name', 'surname', 'phone_number', 'profile_picture']


class UserEventParticipantSerializer(serializers.ModelSerializer):
    profile = ProfileEventParticipantSerializer(read_only=True)
    class Meta:
        model = CentralUser
        fields = ['id', 'email', 'profile']


class EventParticipantSerializer(serializers.ModelSerializer):
    user_profile = UserEventParticipantSerializer(read_only=True)
    class Meta:
        model = EventParticipant
        fields = ['id', 'user_profile', 'role', 'paid_status', 'presense']