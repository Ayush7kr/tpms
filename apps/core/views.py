from django.shortcuts import render


def landing_view(request):
    """
    Renders public institutional landing page with placement metrics and workflow.
    """
    return render(request, 'public/landing.html', {
        'page_title': 'Empowering Careers Through Smarter Placements'
    })


def custom_403_view(request, exception=None):
    return render(request, 'public/error.html', {
        'status_code': 403,
        'error_title': 'Access Restricted',
        'error_message': 'You do not have permission to view or modify this resource.',
    }, status=403)


def custom_404_view(request, exception=None):
    return render(request, 'public/error.html', {
        'status_code': 404,
        'error_title': 'Page Not Found',
        'error_message': 'The requested page or resource could not be found.',
    }, status=404)


def custom_500_view(request):
    return render(request, 'public/error.html', {
        'status_code': 500,
        'error_title': 'Internal Server Error',
        'error_message': 'An unexpected server condition occurred while processing this request.',
    }, status=500)
