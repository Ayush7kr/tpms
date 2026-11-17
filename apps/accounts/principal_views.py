import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from apps.accounts.decorators import principal_required
from apps.accounts.models import User
from apps.departments.models import Department
from apps.students.models import StudentProfile, PlacementStatus
from apps.companies.models import Company
from apps.placements.models import JobOpening
from apps.analytics.services.analytics_service import AnalyticsService


@principal_required
def dashboard_view(request):
    """
    Principal Executive Oversight Dashboard.
    Provides institutional metrics, cross-department comparisons, and Chart.js visuals.
    """
    metrics = AnalyticsService.get_summary_metrics()
    dept_breakdown = AnalyticsService.get_department_breakdown()
    chart_data = AnalyticsService.get_chartjs_payload()

    # Recruiter hiring leaderboard
    top_recruiters = Company.objects.annotate(
        hires_count=Count('hired_students')
    ).filter(hires_count__gt=0).order_by('-hires_count')[:5]

    total_users = User.objects.count()

    return render(request, 'principal_panel/dashboard.html', {
        'metrics': metrics,
        'dept_breakdown': dept_breakdown,
        'chart_data': chart_data,
        'top_recruiters': top_recruiters,
        'total_users': total_users,
        'active_nav': 'dashboard'
    })


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _filtered_students(params):
    """Applies the report filters. Shared by the on-screen report and the CSV export."""
    qs = StudentProfile.objects.select_related('user', 'department', 'placed_company')
    if _num(params.get('min_cgpa')) is not None:
        qs = qs.filter(graduation_cgpa__gte=_num(params.get('min_cgpa')))
    if _num(params.get('min_tenth')) is not None:
        qs = qs.filter(tenth_percentage__gte=_num(params.get('min_tenth')))
    if _num(params.get('min_twelfth')) is not None:
        qs = qs.filter(twelfth_percentage__gte=_num(params.get('min_twelfth')))
    if (params.get('dept_id') or '').isdigit():
        qs = qs.filter(department_id=params.get('dept_id'))
    if (params.get('batch') or '').isdigit():
        qs = qs.filter(batch_year=params.get('batch'))
    if params.get('status'):
        qs = qs.filter(placement_status=params.get('status'))
    query = (params.get('q') or '').strip()
    if query:
        qs = qs.filter(
            Q(roll_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )
    return qs


@principal_required
def department_reports_view(request):
    """
    Department-level analytics and eligibility filtered queries.
    Supports filters for CGPA, 10th%, 12th%, department, graduating batch, and placement status, with pagination.
    """
    min_cgpa = request.GET.get('min_cgpa', '')
    min_tenth = request.GET.get('min_tenth', '')
    min_twelfth = request.GET.get('min_twelfth', '')
    dept_id = request.GET.get('dept_id', '')
    batch = request.GET.get('batch', '')
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    students_qs = _filtered_students(request.GET).order_by('-graduation_cgpa')

    departments = Department.objects.filter(is_active=True).order_by('code')
    batches = StudentProfile.objects.values_list('batch_year', flat=True).distinct().order_by('-batch_year')

    paginator = Paginator(students_qs, 20)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    return render(request, 'principal_panel/department_reports.html', {
        'students': students,
        'departments': departments,
        'batches': batches,
        'statuses': PlacementStatus.choices,
        'selected_dept': dept_id,
        'selected_batch': batch,
        'selected_status': status_filter,
        'min_cgpa': min_cgpa,
        'min_tenth': min_tenth,
        'min_twelfth': min_twelfth,
        'query': query,
        'total_count': students_qs.count(),
        'active_nav': 'departments'
    })


@principal_required
def company_reports_view(request):
    """
    Corporate recruiter participation and hiring breakdown.
    """
    companies = Company.objects.annotate(
        drives_count=Count('job_openings'),
        placed_students_count=Count('hired_students')
    ).order_by('-placed_students_count')

    return render(request, 'principal_panel/company_reports.html', {
        'companies': companies,
        'active_nav': 'companies'
    })


@principal_required
def export_placement_csv_view(request):
    """
    Exports institutional placement records to CSV, preserving active filters if specified.
    """
    students_qs = _filtered_students(request.GET).order_by('department__code', 'roll_number')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="placement_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Roll Number', 'Candidate Name', 'Email', 'Department', 'Batch',
        'CGPA', '10th %', '12th %', 'Placement Status', 'Hiring Company', 'Package (LPA)'
    ])

    for s in students_qs:
        writer.writerow([
            s.roll_number,
            s.user.get_full_name(),
            s.user.email,
            s.department.code,
            s.batch_year,
            s.graduation_cgpa,
            s.tenth_percentage,
            s.twelfth_percentage,
            s.get_placement_status_display(),
            s.placed_company.name if s.placed_company else 'N/A',
            s.salary_package if s.salary_package else 'N/A'
        ])

    return response
