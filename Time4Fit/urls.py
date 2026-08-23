from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_v1_patterns = [
    path('user/', include('user.urls')),
    path('event/', include('event.urls')),
    path('user-profile/', include('user_profile.urls')),
    path('diet/', include('diet.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/v1/', include(api_v1_patterns)),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
