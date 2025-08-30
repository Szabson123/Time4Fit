from django.db import transaction

import uuid

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RegisterUserSerializer, LoginUserSerializer, ResetPasswordUserSerializer, OtpVerifySerializer, ResetPasswordConfirmSerializer
from .utils import gen_code, hmac_code, default_expires
from .models import CentralUser, TwoFactory
from .tasks import send_welcome_email


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

        with transaction.atomic():
            user = serializer.save()

            code_plain = gen_code(6)

            challenge = TwoFactory.objects.create(
                user = user,
                purpose = "register",
                code_hmac = hmac_code(code_plain),
                expires_at = default_expires(ttl_sec)
            )

            message = f"Witaj w Time4Fit twój kod do rejestracji to {code_plain}"
            send_welcome_email.delay(email, message)

        return Response({
            "challenge_id": str(challenge.id),
            "time_valid": minutes_valid,
            "purpose": "register",
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
            
        message = f"Witaj w Time4Fit twój kod do logowania to {code_plain}"
        send_welcome_email.delay(user.email, message)

        return Response({
            "challenge_id": str(challenge.id),
            "time_valid": minutes_valid,
            "purpose": "login"
        }, status=status.HTTP_201_CREATED)


class ResetPasswordView(GenericAPIView):
    serializer_class = ResetPasswordUserSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        email = data["email"]
        
        code_plain = gen_code(6)

        sec_ttl = 300

        try:
            user = CentralUser.objects.get(email=email)
        except CentralUser.DoesNotExist:
            return Response({
                "detail": "Jeśli ten e-mail istnieje, wyślemy kod.",
                "challenge_id": str(uuid.uuid4()),
                "purpose": "reset_password"
            }, status=status.HTTP_200_OK)

        challenge = TwoFactory.objects.create(
            user=user,
            purpose="reset_password",
            code_hmac=hmac_code(code_plain),
            expires_at=default_expires(sec_ttl)
        )

        message = f"Twój kod do zmiany hasła: {code_plain}"
        send_welcome_email.delay(email, message)

        return Response({
            "detail": "Jeśli ten e-mail istnieje, wyślemy kod.",
            "challenge_id": str(challenge.id),
            "purpose": "reset_password"
        }, status=status.HTTP_200_OK)


class OtpVerifyView(GenericAPIView):

    serializer_class = OtpVerifySerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        challenge_id = data["challenge_id"]
        purpose = data["purpose"]
        code = data["code"]

        try:
            ch = TwoFactory.objects.get(id=challenge_id, purpose=purpose)
        except:
            return Response({"detail": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not ch.verify(code_input=code):
            return Response({"detail": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = ch.user
        
        refresh = RefreshToken.for_user(user)

        if purpose == "login":
            return Response(
                {"refresh": str(refresh), "access": str(refresh.access_token)},
                status=status.HTTP_200_OK
            )
            
        if purpose == "register":
            user.is_user_activated = True
            user.save(update_fields=["is_user_activated"])

            return Response(
                {"refresh": "Gratuluję zarejestorowałeś się teraz możesz się zalogować"},
                status=status.HTTP_200_OK
            )

        if purpose == "reset_password":
            sec_ttl = 600
            ticket = TwoFactory.objects.create(
                user=user,
                purpose="reset_password_confirm",
                code_hmac=hmac_code(gen_code(1)),
                expires_at=default_expires(sec_ttl)
            )
            return Response(
                {
                    "reset_ticket_id": str(ticket.id),
                    "time_valid": sec_ttl // 60 or 1,
                    "purpose": "reset_password_confirm"
                },
                status=status.HTTP_200_OK
            )


class ResetPasswordConfirmView(GenericAPIView):
    serializer_class = ResetPasswordConfirmSerializer

    def post(self, request):        
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticket_id = serializer.validated_data["reset_ticket_id"]
        new_password = serializer.validated_data["password"]

        try:
            ticket = TwoFactory.objects.get(id=ticket_id, purpose="reset_password_confirm")
        except TwoFactory.DoesNotExist:
            return Response({"detail": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.is_used or ticket.is_expired:
            return Response({"detail": "invalid_or_expired"}, status=status.HTTP_400_BAD_REQUEST)

        user = ticket.user
        user.set_password(new_password)
        user.is_user_activated = True
        user.save(update_fields=["password", "is_user_activated"])

        ticket.used_at = timezone.now()
        ticket.save(update_fields=["used_at"])

        return Response({"detail": "Hasło zostało zmienione. Możesz się zalogować."}, status=status.HTTP_200_OK)
