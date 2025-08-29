from django.shortcuts import render
from django.db import transaction

from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RegisterUserSerializer, LoginUserSerializer, ResetPasswordUserSerializer
from .utils import gen_code, hmac_code, default_expires
from .models import CentralUser, TwoFactory

from drf_spectacular.utils import extend_schema


class UserRegisterView(GenericAPIView):
    serializer_class = RegisterUserSerializer

    def post(self, request):
        
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        ttl_sec = 300
        minutes_valid = ttl_sec // 60 or 1

        email = data["email"]
        password = data["password"]

        with transaction.atomic():
            user = CentralUser(email=email, is_user_activated=False)
            user.set_password(password)
            user.save()

            code_plain = gen_code(6)

            challenge = TwoFactory.objects.create(
                user = user,
                purpose = "register",
                code_hmac = hmac_code(code_plain),

                expires_at = default_expires(ttl_sec)
            )

            # Send Email with plain code

        return Response({
            "challenge_id": str(challenge.id),
            "time_valid": minutes_valid
        }, status=status.HTTP_201_CREATED)


class UserLoginView(GenericAPIView):
    serializer_class = LoginUserSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]

        sec_ttl = 300
        minutes_valid = sec_ttl // 60 or 1
        code_plain = gen_code(6)

        with transaction.atomic():
            challenge = TwoFactory.objects.create(
                user=user,
                purpose="login",
                code_hmac=hmac_code(code_plain),
                expires_at=default_expires(sec_ttl)
            )
            
        # Send Email

        return Response({
            "challenge_id": str(challenge.id),
            "time_valid": minutes_valid
        }, status=status.HTTP_201_CREATED)


class ResetPasswordView(GenericAPIView):
    serializer_class = ResetPasswordUserSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.error, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.valid_data

        email = data["email"]

        try:
            user = CentralUser.objects.get(email=email)
        except CentralUser.DoesNotExist:
            return Response({"detail": "Jeśli ten e-mail istnieje, wyślemy kod."}, status=200)
        
        code_plain = gen_code(6)

        sec_ttl = 300

        TwoFactory.objects.create(
            user=user,
            purpose="reset_password",
            code_hmac=hmac_code(code_plain),
            expires_at=default_expires(sec_ttl)
        )

        # Send Email

        return Response({"detail": "Jeśli ten e-mail istnieje, wyślemy kod."}, status=200)
