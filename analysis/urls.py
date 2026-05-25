from .views import *
from django.urls import path


urlpatterns = [
    path('create-users-bulk/', BulkCreateUsersView.as_view(), name='change-part-role'),
    path('report-view/', SynchronousReportView.as_view(), name='report-view')
]