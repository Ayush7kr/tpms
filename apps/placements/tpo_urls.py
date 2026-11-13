from django.urls import path
from apps.placements import tpo_views, views

app_name = 'tpo_panel'

urlpatterns = [
    path('', tpo_views.dashboard_view, name='dashboard'),
    path('post-job/', views.post_job_view, name='post_job'),
]
