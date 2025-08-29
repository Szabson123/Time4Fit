from django.shortcuts import render
from django.db import transaction

from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RegisterUserSerializer
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


    