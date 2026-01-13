from .models import Event, EventAdditionalInfo, EventInvitation, SpecialGuests, Category, EventParticipant
from django.utils import timezone
from rest_framework import serializers
from user_profile.models import UserProfile
from user.models import CentralUser
import random, string
from decimal import Decimal
from django.db import transaction

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class SpecialGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialGuests
        fields = ['id', 'name', 'surname', 'nickname']


class EventAdditionalInfoSerializer(serializers.ModelSerializer):
    special_guests = SpecialGuestSerializer(many=True, required=False)
    class Meta:

        model = EventAdditionalInfo
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'price', 'payment_in_app', 'special_guests']
    
    def validate(self, attrs):
        
        return super().validate(attrs)
    
    def create(self, validated_data):
        guest_data = validated_data.pop("special_guests", [])
        event = self.context.get("event")
        add_info = EventAdditionalInfo.objects.create(event=event, **validated_data)
    
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
    event_participant_count = serializers.IntegerField(read_only=True)
    author_full_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        read_only_fields = ['unique_id', 'author']
        fields = ['id', 'unique_id', 'author', 'author_full_name', 'title', 'category', 'short_desc', 'long_desc', 'date_time_event', 'duration_min',
                'latitude', 'longitude', 'public_event',
                'country', 'city', 'street', 'street_number', 'flat_number', 'zip_code', 'event_participant_count',
                'additional_info']
        
    def validate_date_time_event(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("You cant create event in the past")
        return value
    
    def get_author_full_name(self, obj):
        author = obj.author
        if not author:
            return None
        return f"{author.profile.name} {author.profile.surname}"
    
    @transaction.atomic
    def create(self, validated_data):
        additional_info_data = validated_data.pop("additional_info")
        event = Event.objects.create(**validated_data)

        info_ser = EventAdditionalInfoSerializer(data=additional_info_data, context={'event': event})
        info_ser.is_valid(raise_exception=True)
        info_ser.save()

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
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'price']


class EventListSerializer(serializers.ModelSerializer):
    additional_info = EventAdditionalInfoListSerializer(read_only=True)
    category_name = serializers.SerializerMethodField()
    event_participant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'date_time_event', 'title', 'short_desc', 'category_name', 'event_participant_count',
                  'country', 'city', 'street', 'street_number', 'flat_number', 'additional_info']
        
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
        fields = ['id', 'user', 'role', 'paid_status', 'presence']


class EventInvitationSerializer(serializers.ModelSerializer):
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = EventInvitation
        fields = ['id', 'code', 'created_at', 'is_one_use', 'is_valid', 'link']


class EventInvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventInvitation
        fields = ['is_one_use', 'is_active']

    def create(self, validated_data):
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not EventInvitation.objects.filter(code=code).exists():
                validated_data["code"] = code
                break

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
    event_participant_count = serializers.IntegerField(read_only=True)

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

        if not inv.is_valid:
            raise serializers.ValidationError("Invitation expired or inactive.")

        return value
    

class NoneSerializer(serializers.Serializer):
    pass


class ChangeRoleSerializer(serializers.Serializer):
    new_role = serializers.CharField(required=True)


class EventMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'latitude', 'longitude']
