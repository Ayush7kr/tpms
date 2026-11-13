from django.utils import timezone
from apps.placements.models import JobOpening, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication


class EligibilityEngine:
    @staticmethod
    def evaluate(student_profile, job_opening):
        """
        Evaluates candidate metrics against job cut-off criteria.
        Returns a dictionary containing boolean verdict, failed criteria details,
        application status, and deadline state.
        """
        failed_criteria = []

        # 1. Department eligibility check
        allowed_depts = job_opening.allowed_departments.all()
        if student_profile.department not in allowed_depts:
            dept_codes = ", ".join([d.code for d in allowed_depts])
            failed_criteria.append(f"Department {student_profile.department.code} is not eligible (Allowed: {dept_codes}).")

        # 2. Department assistant approval check
        approval = DepartmentJobApproval.objects.filter(
            job_opening=job_opening,
            department=student_profile.department
        ).first()

        if not approval or approval.status != ApprovalStatus.APPROVED:
            failed_criteria.append(f"Drive is pending activation by your Department TnP Coordinator.")

        # 3. Batch year check
        if job_opening.allowed_batches:
            batches = [b.strip() for b in job_opening.allowed_batches.split(',') if b.strip()]
            if str(student_profile.batch_year) not in batches:
                failed_criteria.append(f"Batch {student_profile.batch_year} not eligible (Target: {job_opening.allowed_batches}).")

        # 4. 10th Percentage Cut-off
        if job_opening.min_tenth_percentage > 0:
            if student_profile.tenth_percentage < job_opening.min_tenth_percentage:
                failed_criteria.append(
                    f"10th Score ({student_profile.tenth_percentage}%) below required cut-off ({job_opening.min_tenth_percentage}%)."
                )

        # 5. 12th Percentage Cut-off
        if job_opening.min_twelfth_percentage > 0:
            if student_profile.twelfth_percentage < job_opening.min_twelfth_percentage:
                failed_criteria.append(
                    f"12th Score ({student_profile.twelfth_percentage}%) below required cut-off ({job_opening.min_twelfth_percentage}%)."
                )

        # 6. Graduation CGPA Cut-off
        if job_opening.min_graduation_cgpa > 0:
            if student_profile.graduation_cgpa < job_opening.min_graduation_cgpa:
                failed_criteria.append(
                    f"Graduation CGPA ({student_profile.graduation_cgpa}) below required cut-off ({job_opening.min_graduation_cgpa})."
                )

        # 7. Active Backlogs Limit
        if student_profile.active_backlogs > job_opening.max_active_backlogs:
            failed_criteria.append(
                f"Active Backlogs ({student_profile.active_backlogs}) exceeds permitted maximum ({job_opening.max_active_backlogs})."
            )

        # Existing Application Check
        existing_application = JobApplication.objects.filter(
            job_opening=job_opening,
            student=student_profile
        ).first()

        # Deadline Check
        deadline = job_opening.application_deadline
        if isinstance(deadline, str):
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(deadline)
            if parsed:
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(parsed)
                deadline = parsed

        if deadline:
            if hasattr(deadline, 'tzinfo') and timezone.is_naive(deadline):
                deadline = timezone.make_aware(deadline)
            try:
                is_deadline_passed = timezone.now() > deadline
            except TypeError:
                is_deadline_passed = False
        else:
            is_deadline_passed = False
        is_eligible = len(failed_criteria) == 0

        can_apply = is_eligible and not is_deadline_passed and existing_application is None and job_opening.status == 'PUBLISHED'

        return {
            'is_eligible': is_eligible,
            'can_apply': can_apply,
            'failed_criteria': failed_criteria,
            'has_applied': existing_application is not None,
            'application': existing_application,
            'is_deadline_passed': is_deadline_passed
        }
