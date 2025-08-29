from rest_framework import serializers
from .models import CentralUser

class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate_password(self, value):
        if len(value) <= 8:
            raise serializers.ValidationError("Password is to short")
        return value
    
    def validate_email(self, value):
        if CentralUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Taki user już istnieje")
        
        return value