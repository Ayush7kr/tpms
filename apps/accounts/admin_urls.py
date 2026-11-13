from django.urls import path
from apps.accounts import admin_views

app_name = 'admin_panel'

urlpatterns = [
    path('', admin_views.dashboard_view, name='dashboard'),
    path('users/', admin_views.users_list_view, name='users'),
    path('users/create/', admin_views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', admin_views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/toggle/', admin_views.user_toggle_status_view, name='user_toggle'),
    path('users/<int:user_id>/delete/', admin_views.user_delete_view, name='user_delete'),
    path('departments/', admin_views.departments_list_view, name='departments'),
    path('departments/create/', admin_views.department_create_view, name='department_create'),
    path('departments/<int:dept_id>/edit/', admin_views.department_edit_view, name='department_edit'),
    path('departments/<int:dept_id>/delete/', admin_views.department_delete_view, name='department_delete'),
    path('assignments/', admin_views.assistant_assignments_view, name='assistant_assignments'),
    path('audit/', admin_views.audit_logs_view, name='audit_logs'),
]
