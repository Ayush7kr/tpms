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

    students_qs = StudentProfile.objects.select_related('user', 'department', 'placed_company').all().order_by('-graduation_cgpa')

    if min_cgpa:
        try:
            students_qs = students_qs.filter(graduation_cgpa__gte=float(min_cgpa))
        except ValueError:
            pass
    if min_tenth:
        try:
            students_qs = students_qs.filter(tenth_percentage__gte=float(min_tenth))
        except ValueError:
            pass
    if min_twelfth:
        try:
            students_qs = students_qs.filter(twelfth_percentage__gte=float(min_twelfth))
        except ValueError:
            pass
    if dept_id:
        students_qs = students_qs.filter(department_id=dept_id)
    if batch:
        students_qs = students_qs.filter(batch_year=batch)
    if status_filter:
        students_qs = students_qs.filter(placement_status=status_filter)
    if query:
        students_qs = students_qs.filter(
            Q(roll_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )

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
    min_cgpa = request.GET.get('min_cgpa', '')
    dept_id = request.GET.get('dept_id', '')
    batch = request.GET.get('batch', '')
    status_filter = request.GET.get('status', '')

    students_qs = StudentProfile.objects.select_related('user', 'department', 'placed_company').order_by('department__code', 'roll_number')

    if min_cgpa:
        try:
            students_qs = students_qs.filter(graduation_cgpa__gte=float(min_cgpa))
        except ValueError:
            pass
    if dept_id:
        students_qs = students_qs.filter(department_id=dept_id)
    if batch:
        students_qs = students_qs.filter(batch_year=batch)
    if status_filter:
        students_qs = students_qs.filter(placement_status=status_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tpms_institutional_placement_report.csv"'

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
