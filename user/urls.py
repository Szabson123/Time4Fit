from django.urls import path, include

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import UserRegisterView, CurrentUserView, UserLoginView, ResetPasswordView, OtpVerifyView, ResetPasswordConfirmView, UserInfoAndSettingsInfoViewSet

urlpatterns = [
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('login/', UserLoginView.as_view(), name='token_obtain_pair'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('reset_password/', ResetPasswordView.as_view(), name='reset_password'),

    path('settings/', UserInfoAndSettingsInfoViewSet.as_view(), name='settings'),

    path('otp_verify/', OtpVerifyView.as_view(), name='otp_verify'),
    path("reset-password/confirm/", ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),
    path('me/', CurrentUserView.as_view(), name='me'),
]