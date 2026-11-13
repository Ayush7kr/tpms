from django.urls import path
from apps.placements import views

app_name = 'placements'

urlpatterns = [
    path('', views.drives_list_view, name='drives_list'),
    path('<int:job_id>/', views.drive_detail_view, name='drive_detail'),
    path('<int:job_id>/edit/', views.job_edit_view, name='job_edit'),
    path('post/', views.post_job_view, name='post_job'),
]
