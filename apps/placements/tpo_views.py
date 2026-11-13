from django.shortcuts import render
from django.db.models import Count, Avg, Min, Max, Q
from apps.accounts.decorators import tpo_required
from apps.accounts.models import User
from apps.departments.models import Department
from apps.students.models import StudentProfile, PlacementStatus
from apps.placements.models import JobOpening
from apps.companies.models import Company
from apps.applications.models import JobApplication


@tpo_required
def dashboard_view(request):
    """
    Central TnP Officer Operational Dashboard.
    Provides macro metrics: counts of students, drives, placed/unplaced, and package stats (min/avg/max).
    """
    total_users = User.objects.count()
    total_departments = Department.objects.count()
    total_students = StudentProfile.objects.count()
    placed_students = StudentProfile.objects.filter(placement_status=PlacementStatus.PLACED).count()
    unplaced_students = StudentProfile.objects.filter(placement_status=PlacementStatus.UNPLACED).count()

    active_job_openings = JobOpening.objects.filter(status='PUBLISHED').count()
    total_companies = Company.objects.filter(is_active=True).count()
    total_applications = JobApplication.objects.count()

    # Package Statistics (min / avg / max)
    placed_with_pkg = StudentProfile.objects.filter(placement_status=PlacementStatus.PLACED, salary_package__isnull=False)
    pkg_stats = placed_with_pkg.aggregate(
        min_pkg=Min('salary_package'),
        avg_pkg=Avg('salary_package'),
        max_pkg=Max('salary_package')
    )

    min_package = pkg_stats['min_pkg'] or 0.0
    avg_package = round(pkg_stats['avg_pkg'] or 0.0, 2)
    max_package = pkg_stats['max_pkg'] or 0.0

    # Department-wise student breakdown
    dept_stats = Department.objects.annotate(
        total_stu=Count('students'),
        placed_stu=Count('students', filter=Q(students__placement_status='PLACED')),
        unplaced_stu=Count('students', filter=Q(students__placement_status='UNPLACED'))
    )

    # Recent drives
    recent_drives = JobOpening.objects.select_related('company').order_by('-created_at')[:5]

    return render(request, 'tpo_panel/dashboard.html', {
        'total_users': total_users,
        'total_departments': total_departments,
        'total_students': total_students,
        'placed_students': placed_students,
        'unplaced_students': unplaced_students,
        'active_job_openings': active_job_openings,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'min_package': min_package,
        'avg_package': avg_package,
        'max_package': max_package,
        'dept_stats': dept_stats,
        'recent_drives': recent_drives,
        'active_nav': 'dashboard'
    })
