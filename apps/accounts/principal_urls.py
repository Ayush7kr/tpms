from django.urls import path
from apps.accounts import principal_views

app_name = 'principal_panel'

urlpatterns = [
    path('', principal_views.dashboard_view, name='dashboard'),
    path('departments/', principal_views.department_reports_view, name='department_reports'),
    path('companies/', principal_views.company_reports_view, name='company_reports'),
    path('export/csv/', principal_views.export_placement_csv_view, name='export_csv'),
]
