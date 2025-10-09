from .models import Event, EventAdditionalInfo, EventInvitation, SpecialGuests, Category, EventParticipant
from django.utils import timezone
from rest_framework import serializers
from user_profile.models import UserProfile
from user.models import CentralUser
import random, string
from decimal import Decimal

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
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'participant_list_show', 'free', 'price', 'payment_in_app', 'special_guests']

    def validate(self, data):
        if data.get('free') and data.get('price') and data['price'] != Decimal("0.00"):
            raise serializers.ValidationError({
                "price": "If 'free' is true, price must be 0.00."
            })
        return data
    
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
                'latitude', 'longitude', 'public_event',
                'country', 'city', 'street', 'street_number', 'flat_number', 'zip_code', 'event_participant_count',
                'additional_info']
        
    def validate_date_time_event(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("You cant create event in the past")
        return value
        
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

class EventAdditionalInfoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAdditionalInfo
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'true_price']


class EventListSerializer(serializers.ModelSerializer):
    additional_info = EventAdditionalInfoListSerializer(read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'date_time_event', 'title', 'short_desc', 'category_name', 'additional_info', 'event_participant_count']
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None


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
    user = UserEventParticipantSerializer(read_only=True)
    class Meta:
        model = EventParticipant
        fields = ['id', 'user', 'role', 'paid_status', 'presense']


class EventInvitationSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()
    class Meta:
        model = EventInvitation
        fields = ['id', 'code', 'date_added', 'is_one_use', 'is_valid', 'link']

    def get_is_valid(self, obj):
        return obj.is_active and timezone.now() < obj.event.date_time_event


class EventInvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventInvitation
        fields = ['is_one_use', 'is_active']

    def create(self, validated_data):
        validated_data["code"] = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        validated_data["is_active"] = True
        return super().create(validated_data)


class ProfileEvenSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['name', 'surname']


class EventSimpleSerializer(serializers.ModelSerializer):
    profile = ProfileEvenSimpleSerializer(read_only=True)
    class Meta:
        model = CentralUser
        fields = ['id', 'profile']


class EventInvSerializer(serializers.ModelSerializer):
    author = EventSimpleSerializer(read_only=True)
    additional_info = EventAdditionalInfoListSerializer(read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'author', 'category_name', 'title', 'additional_info', 'event_participant_count']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    

class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)

    def validate_code(self, value):
        try:
            inv = EventInvitation.objects.get(code=value)
        except EventInvitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation code.")

        if not inv.is_valid_code:
            raise serializers.ValidationError("Invitation expired or inactive.")

        return value
    

class NoneSerializer(serializers.Serializer):
    pass