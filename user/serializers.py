from rest_framework import serializers
from .models import CentralUser


class RegisterUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)
    class Meta:
        model = CentralUser
        fields = ['email', 'password', 'first_name', 'last_name', 'phone_number']

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password is too short")
        return value
    
    def validate_email(self, value):
        if CentralUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User exists")
        
        return value
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CentralUser(**validated_data)
        user.set_password(password)
        user.is_user_activated = False
        user.save()
        return user
    

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
    

class ResetPasswordUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
