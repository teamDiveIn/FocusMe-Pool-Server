from django.urls import path
from . import views

urlpatterns = [
    path('test', views.test),
    path('interest/create', views.create_interest_for_test),
    path('', views.pools),
    path('register', views.register),
    path('enter', views.enter),
    path('leave', views.leave),
    path('back', views.leave),
    path('exit', views.exit_with_reward)
]
