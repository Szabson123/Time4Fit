from rest_framework import serializers
from .models import CentralUser
from user_profile.models import UserProfile


class RegisterUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
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
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        phone_number = validated_data.pop("phone_number")

        password = validated_data.pop("password")
        user = CentralUser(**validated_data)
        user.set_password(password)
        user.is_user_activated = False
        user.save()

        UserProfile.objects.create(
            user=user,
            name=first_name,
            surname=last_name,
            phone_number=phone_number
        )
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
            raise serializers.ValidationError("Invalid credentials")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        data["user"] = user
        return data
    

class ResetPasswordUserSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OtpVerifySerializer(serializers.Serializer):
    challenge_id = serializers.CharField()
    purpose = serializers.CharField()
    code = serializers.CharField()


class ResetPasswordConfirmSerializer(serializers.Serializer):
    reset_ticket_id = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password is too short")
        return value