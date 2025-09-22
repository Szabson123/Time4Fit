from .models import Event, EventAdditionalInfo
from rest_framework import serializers


class EventAdditionalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAdditionalInfo
        fields = ['advanced_level', 'places_for_people_limit', 'age_limit', 'participant_list_show', 'public_event', 'free', 'price', 'payment_in_app']


class EventSerializer(serializers.ModelSerializer):
    additional_info = EventAdditionalInfoSerializer()

    class Meta:
        model = Event
        fields = ['id', 'unique_id', 'author', 'title', 'category', 'short_desc', 'long_desc', 'date_time_event', 'duration_min',
                  'latitude', 'longitude',
                  'country', 'city', 'street', 'street_number', 'flat_number', 'zip_code',
                   'additional_info']
        
    def create(self, validated_data):
        additional_info_data = validated_data.pop("additional_info")
        event = Event.objects.create(**validated_data)
        EventAdditionalInfo.objects.create(event=event, **additional_info_data)
        return event
    
    def update(self, instance, validated_data):
        additional_info_data = validated_data.pop("additional_info", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        additional_info = instance.additional_info
        for attr, value in additional_info_data.items():
            setattr(additional_info, attr, value)
        additional_info.save()

        return instance