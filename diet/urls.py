from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (DailyMealCalendarDetailView)


urlpatterns = [
    path('daily-meals/', DailyMealCalendarDetailView.as_view(), name='daily-meals')
]