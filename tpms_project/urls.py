from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Core public routes & landing page
    path('', include('apps.core.urls', namespace='core')),
    
    # Custom Authentication routes
    path('auth/', include('apps.accounts.urls', namespace='accounts')),

    # Role Dashboards and Panels
    path('admin-panel/', include('apps.accounts.admin_urls', namespace='admin_panel')),
    path('principal/', include('apps.accounts.principal_urls', namespace='principal_panel')),
    path('tpo/', include('apps.placements.tpo_urls', namespace='tpo_panel')),
    path('assistant/', include('apps.departments.assistant_urls', namespace='assistant_panel')),
    path('student/', include('apps.students.student_urls', namespace='student_panel')),
    path('student/career-assistant/', include('apps.career_assistant.urls', namespace='career_assistant')),

    # Shared feature routes
    path('students/', include('apps.students.urls', namespace='students')),
    path('companies/', include('apps.companies.urls', namespace='companies')),
    path('placements/', include('apps.placements.urls', namespace='placements')),
    path('applications/', include('apps.applications.urls', namespace='applications')),
    path('study-materials/', include('apps.study_materials.urls', namespace='study_materials')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
