from django.urls import path
from . import views

urlpatterns = [
    path('', views.pools),
    path('register', views.register),
    path('enter', views.enter),
    path('leave', views.leave),
    path('back', views.back),
    path('exit', views.exit_with_reward),
    path('thumbnail', views.thumbnail)
]
