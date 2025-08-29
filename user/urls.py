from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import UserRegisterView, UserLoginView, ResetPasswordView

urlpatterns = [
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('login/', UserLoginView.as_view(), name='token_obtain_pair'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('reset_password', ResetPasswordView.as_view(), name='reset_password')
]