from django.urls import path
from apps.departments import assistant_views

app_name = 'assistant_panel'

urlpatterns = [
    path('', assistant_views.dashboard_view, name='dashboard'),
    path('students/', assistant_views.student_roster_view, name='student_roster'),
    path('students/create/', assistant_views.student_create_view, name='student_create'),
    path('students/<int:student_id>/edit/', assistant_views.student_edit_view, name='student_edit'),
    path('approvals/', assistant_views.job_approvals_view, name='job_approvals'),
    path('verify/', assistant_views.verify_applications_view, name='verify_applications'),
]
