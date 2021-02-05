"""DiveIn_Pool_Server URL Configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pool/', include('pool.urls')),
]
