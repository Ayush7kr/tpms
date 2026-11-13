from django.urls import path
from apps.study_materials import views

app_name = 'study_materials'

urlpatterns = [
    path('', views.materials_list_view, name='list'),
    path('upload/', views.material_upload_view, name='upload'),
]
