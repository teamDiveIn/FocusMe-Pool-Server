"""DiveIn_Pool_Server URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_jwt.views import verify_jwt_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/verify/', verify_jwt_token),
    path('pool/', include('pool.urls')),
]
