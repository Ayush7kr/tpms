from django.urls import path
from apps.students import views

app_name = 'students'

urlpatterns = [
    path('import/', views.bulk_import_view, name='bulk_import'),
    path('template/<str:format_type>/', views.download_template_view, name='download_template'),
    path('<int:student_id>/', views.student_detail_view, name='detail'),
    path('<int:student_id>/resume/', views.student_resume_download_view, name='download_resume'),
]
