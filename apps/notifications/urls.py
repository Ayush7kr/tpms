from django.urls import path
from apps.accounts import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_view, name='list'),
]
