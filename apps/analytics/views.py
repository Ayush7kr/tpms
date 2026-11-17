from django.shortcuts import render
from apps.accounts.decorators import role_required

STAFF_ROLES = ['ADMIN', 'PRINCIPAL', 'TNP_OFFICER', 'TNP_ASSISTANT']
from apps.analytics.services.analytics_service import AnalyticsService


@role_required(STAFF_ROLES)
def placement_stats_view(request):
    """
    Renders placement visual analytics with Chart.js charts.
    """
    metrics = AnalyticsService.get_summary_metrics()
    dept_breakdown = AnalyticsService.get_department_breakdown()
    chart_data = AnalyticsService.get_chartjs_payload()

    return render(request, 'analytics/placement_stats.html', {
        'metrics': metrics,
        'dept_breakdown': dept_breakdown,
        'chart_data': chart_data,
        'active_nav': 'analytics'
    })


@role_required(STAFF_ROLES)
def salary_stats_view(request):
    """
    Renders salary benchmark insights (Min/Avg/Max CTC).
    """
    metrics = AnalyticsService.get_summary_metrics()
    dept_breakdown = AnalyticsService.get_department_breakdown()
    chart_data = AnalyticsService.get_chartjs_payload()

    return render(request, 'analytics/salary_stats.html', {
        'metrics': metrics,
        'dept_breakdown': dept_breakdown,
        'chart_data': chart_data,
        'active_nav': 'salary'
    })
