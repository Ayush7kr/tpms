from apps.students.models import StudentProfile
from apps.applications.models import JobApplication
from apps.placements.models import JobOpening
from apps.study_materials.models import StudyMaterial


class StudentCareerContextBuilder:
    """
    Safely builds the minimum necessary personalized institutional context
    for the authenticated student. Enforces strict privacy and ownership isolation.
    """

    @classmethod
    def build_context(cls, student_profile: StudentProfile, query: str = "") -> dict:
        if not student_profile:
            return {}

        # 1. Academic & Personal Placement Profile
        profile_data = {
            'name': student_profile.user.get_full_name(),
            'roll_number': student_profile.roll_number,
            'department_code': student_profile.department.code,
            'department_name': student_profile.department.name,
            'batch_year': student_profile.batch_year,
            'degree': student_profile.degree,
            'graduation_cgpa': float(student_profile.graduation_cgpa or 0.0),
            'tenth_percentage': float(student_profile.tenth_percentage or 0.0),
            'twelfth_percentage': float(student_profile.twelfth_percentage or 0.0),
            'active_backlogs': student_profile.active_backlogs,
            'skills': [s.strip() for s in (student_profile.skills or '').split(',') if s.strip()],
            'has_resume': bool(student_profile.resume),
            'placement_status': student_profile.placement_status,
            'placed_details': None
        }

        if student_profile.placement_status == 'PLACED' and student_profile.placed_company:
            profile_data['placed_details'] = {
                'company': student_profile.placed_company.name,
                'package': float(student_profile.salary_package or 0.0)
            }

        # 2. Student's Active Applications
        apps_qs = JobApplication.objects.filter(
            student=student_profile
        ).select_related('job_opening__company')[:6]

        applications = [
            {
                'company': app.job_opening.company.name,
                'title': app.job_opening.title,
                'package': float(app.job_opening.package_ctc),
                'stage': app.get_stage_display(),
                'status': app.stage
            }
            for app in apps_qs
        ]

        # 3. Active Eligible/Published Campus Drives in TPMS
        drives_qs = JobOpening.objects.filter(
            status='PUBLISHED'
        ).select_related('company').prefetch_related('allowed_departments')[:8]

        active_drives = [
            {
                'id': d.id,
                'company': d.company.name,
                'title': d.title,
                'package': float(d.package_ctc),
                'location': d.job_location,
                'min_cgpa': float(d.min_graduation_cgpa),
                'max_backlogs': d.max_active_backlogs,
                'role_description': d.role_description[:250],
                'drive_date': d.drive_date.strftime('%b %d, %Y') if d.drive_date else 'TBD'
            }
            for d in drives_qs
        ]

        # 4. Relevant TPMS Preparation Resources
        materials_qs = StudyMaterial.objects.select_related('department').order_by('-created_at')[:8]
        resources = [
            {
                'id': m.id,
                'title': m.title,
                'category': m.get_category_display(),
                'type': m.get_resource_type_display(),
                'url': '/study-materials/'
            }
            for m in materials_qs
        ]

        # 5. Targeted Query Detection (e.g. mentions of a specific company)
        matched_drive = None
        q_lower = query.lower() if query else ""
        for d in active_drives:
            if d['company'].lower() in q_lower or d['title'].lower() in q_lower:
                matched_drive = d
                break

        return {
            'student': profile_data,
            'applications': applications,
            'active_drives': active_drives,
            'matched_drive': matched_drive,
            'study_resources': resources
        }
