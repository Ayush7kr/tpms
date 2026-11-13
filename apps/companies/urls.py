from django.urls import path
from apps.companies import views

app_name = 'companies'

urlpatterns = [
    path('', views.company_list_view, name='list'),
    path('create/', views.company_create_view, name='create'),
    path('<int:company_id>/', views.company_detail_view, name='detail'),
    path('<int:company_id>/edit/', views.company_edit_view, name='edit'),
]
