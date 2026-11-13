from django.urls import path
from apps.analytics import views

app_name = 'analytics'

urlpatterns = [
    path('placement/', views.placement_stats_view, name='placement_stats'),
    path('salary/', views.salary_stats_view, name='salary_stats'),
]
