from django.db.models import Count, Avg, Min, Max, Q, F
from apps.departments.models import Department
from apps.students.models import StudentProfile, PlacementStatus
from apps.companies.models import Company
from apps.placements.models import JobOpening
from apps.applications.models import JobApplication


class AnalyticsService:
    @staticmethod
    def get_summary_metrics():
        total_students = StudentProfile.objects.count()
        placed_students = StudentProfile.objects.filter(placement_status=PlacementStatus.PLACED).count()
        unplaced_students = StudentProfile.objects.filter(placement_status=PlacementStatus.UNPLACED).count()

        placement_rate = round((placed_students / total_students * 100), 1) if total_students > 0 else 0.0

        pkg_stats = StudentProfile.objects.filter(
            placement_status=PlacementStatus.PLACED,
            salary_package__isnull=False
        ).aggregate(
            min_pkg=Min('salary_package'),
            avg_pkg=Avg('salary_package'),
            max_pkg=Max('salary_package')
        )

        return {
            'total_students': total_students,
            'placed_students': placed_students,
            'unplaced_students': unplaced_students,
            'placement_rate': placement_rate,
            'min_pkg': pkg_stats['min_pkg'] or 0.0,
            'avg_pkg': round(pkg_stats['avg_pkg'] or 0.0, 2),
            'max_pkg': pkg_stats['max_pkg'] or 0.0,
            'active_drives': JobOpening.objects.filter(status='PUBLISHED').count(),
            'total_companies': Company.objects.filter(is_active=True).count(),
        }

    @staticmethod
    def get_department_breakdown():
        departments = Department.objects.annotate(
            total_students=Count('students'),
            placed_students=Count('students', filter=Q(students__placement_status=PlacementStatus.PLACED)),
            unplaced_students=Count('students', filter=Q(students__placement_status=PlacementStatus.UNPLACED)),
            avg_pkg=Avg('students__salary_package', filter=Q(students__placement_status=PlacementStatus.PLACED))
        ).order_by('code')

        results = []
        for d in departments:
            rate = round((d.placed_students / d.total_students * 100), 1) if d.total_students > 0 else 0.0
            results.append({
                'code': d.code,
                'name': d.name,
                'total': d.total_students,
                'placed': d.placed_students,
                'unplaced': d.unplaced_students,
                'rate': rate,
                'avg_pkg': round(d.avg_pkg or 0.0, 2)
            })
        return results

    @staticmethod
    def get_chartjs_payload():
        """
        Formats data arrays for Chart.js bar, doughnut, and line charts.
        """
        dept_data = AnalyticsService.get_department_breakdown()

        labels = [d['code'] for d in dept_data]
        enrolled = [d['total'] for d in dept_data]
        placed = [d['placed'] for d in dept_data]

        # Salary tier distribution
        placed_students = StudentProfile.objects.filter(placement_status=PlacementStatus.PLACED, salary_package__isnull=False)
        tier_1 = placed_students.filter(salary_package__gte=12.0).count()
        tier_2 = placed_students.filter(salary_package__gte=6.0, salary_package__lt=12.0).count()
        tier_3 = placed_students.filter(salary_package__lt=6.0).count()

        return {
            'dept_labels': labels,
            'dept_enrolled': enrolled,
            'dept_placed': placed,
            'tier_distribution': [tier_1, tier_2, tier_3],
            'tier_labels': ['Dream (12+ LPA)', 'Core (6-12 LPA)', 'Mass (under 6 LPA)']
        }
