from django.urls import path
from apps.applications import views

app_name = 'applications'

urlpatterns = [
    path('apply/<int:job_id>/', views.apply_view, name='apply'),
    path('<int:application_id>/withdraw/', views.withdraw_application_view, name='withdraw'),
    path('tracker/', views.central_tracker_view, name='central_tracker'),
    path('<int:application_id>/stage/', views.update_stage_view, name='update_stage'),
]
