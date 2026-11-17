from django.shortcuts import render
from django.utils import timezone


def landing_view(request):
    """Public landing page. Every number shown is read from the database."""
    from apps.analytics.services.analytics_service import AnalyticsService
    from apps.companies.models import Company
    from apps.placements.models import JobOpening

    metrics = AnalyticsService.get_summary_metrics()
    open_drives = (
        JobOpening.objects.filter(status='PUBLISHED', application_deadline__gte=timezone.now())
        .select_related('company')
        .prefetch_related('allowed_departments')
        .order_by('application_deadline')[:4]
    )
    recruiters = Company.objects.filter(is_active=True).order_by('name')

    return render(request, 'public/landing.html', {
        'metrics': metrics,
        'open_drives': open_drives,
        'recruiters': recruiters,
    })


def custom_403_view(request, exception=None):
    return render(request, 'public/error.html', {
        'status_code': 403,
        'error_title': "You don't have access to this page",
        'error_message': 'This page belongs to a different role. If you think you should have access, contact the placement office.',
    }, status=403)


def custom_404_view(request, exception=None):
    return render(request, 'public/error.html', {
        'status_code': 404,
        'error_title': 'Page not found',
        'error_message': 'The link may be out of date, or the drive or record was removed.',
    }, status=404)


def custom_500_view(request):
    return render(request, 'public/error.html', {
        'status_code': 500,
        'error_title': 'Something went wrong on our side',
        'error_message': 'The error has been logged. Try again in a minute; if it keeps happening, tell the placement office what you were doing.',
    }, status=500)
