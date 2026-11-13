from django.urls import path
from apps.students import student_views

app_name = 'student_panel'

urlpatterns = [
    path('', student_views.dashboard_view, name='dashboard'),
    path('jobs/', student_views.eligible_jobs_view, name='eligible_jobs'),
    path('applications/', student_views.my_applications_view, name='my_applications'),
    path('profile/', student_views.profile_view, name='profile'),
]
