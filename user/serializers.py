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
            raise serializers.ValidationError("User does not exist")
        
        return value
    

class LoginUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data["email"]
        password = data["password"]

        try:
            user = CentralUser.objects.get(email=email, is_user_activated=True)
        except CentralUser.DoesNotExist:
            raise serializers.ValidationError("User does not exist or is not activated")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        data["user"] = user
        return data