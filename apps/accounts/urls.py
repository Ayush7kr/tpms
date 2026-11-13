from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.role_redirect_view, name='role_redirect'),
    path('switch/<str:role>/', views.quick_switch_view, name='quick_switch'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('change-password/', views.change_password_view, name='change_password'),
]
