from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.companies.models import Company
from apps.departments.models import Department
from apps.accounts.decorators import login_required_custom, tpo_required, role_required
from apps.accounts.models import UserRole
from apps.departments.assistant_views import get_assistant_departments
from apps.placements.services.eligibility import EligibilityEngine
from apps.applications.models import JobApplication
from apps.audit.models import AuditLog
from apps.notifications.models import Notification


@login_required_custom
def drives_list_view(request):
    """
    Lists placement drives with status filter, instant search, and pagination.
    """
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    drives_qs = JobOpening.objects.select_related('company').prefetch_related('allowed_departments').all().order_by('-created_at')

    if status_filter:
        drives_qs = drives_qs.filter(status=status_filter)
    if query:
        drives_qs = drives_qs.filter(
            Q(title__icontains=query) |
            Q(company__name__icontains=query) |
            Q(job_location__icontains=query)
        )

    paginator = Paginator(drives_qs, 12)
    page_number = request.GET.get('page')
    drives = paginator.get_page(page_number)

    return render(request, 'placements/drives_list.html', {
        'drives': drives,
        'selected_status': status_filter,
        'statuses': JobStatus.choices,
        'query': query,
        'total_count': drives_qs.count(),
        'active_nav': 'drives'
    })


@login_required_custom
def drive_detail_view(request, job_id):
    """
    Detailed inspection of a specific placement drive, cut-off matrix, and applicants.
    - Students: Candidate roster hidden; personal application status & eligibility displayed.
    - Assistants: Candidate roster filtered strictly to assigned department(s).
    - Leadership (Admin, Principal, TPO): Full candidate roster displayed.
    """
    job = get_object_or_404(
        JobOpening.objects.select_related('company').prefetch_related('allowed_departments', 'applications__student__user', 'department_approvals__department'),
        id=job_id
    )

    approvals = job.department_approvals.all()
    all_apps = job.applications.select_related('student__user', 'student__department').order_by('-applied_at')

    student_application = None
    eligibility = None
    applications = all_apps

    if request.user.role == UserRole.STUDENT:
        student_profile = getattr(request.user, 'student_profile', None)
        if student_profile:
            student_application = all_apps.filter(student=student_profile).first()
            eligibility = EligibilityEngine.evaluate(student_profile, job)
        applications = JobApplication.objects.none()
    elif request.user.role == UserRole.TNP_ASSISTANT:
        assigned_depts = get_assistant_departments(request.user)
        applications = all_apps.filter(student__department__in=assigned_depts)

    return render(request, 'placements/drive_detail.html', {
        'job': job,
        'approvals': approvals,
        'applications': applications,
        'student_application': student_application,
        'eligibility': eligibility,
        'active_nav': 'drives'
    })


@role_required(['TNP_OFFICER', 'ADMIN', 'TNP_ASSISTANT'])
def post_job_view(request):
    """
    Creates a new placement drive opening with multi-metric cut-off criteria.
    - TPO/Admin can post drives for any/all departments (with branch approvals pending).
    - TnP Assistants can post drives directly for their assigned department(s), which are automatically approved.
    Strictly NO Django Forms.
    """
    companies = Company.objects.filter(is_active=True).order_by('name')
    if request.user.role == UserRole.TNP_ASSISTANT:
        departments = get_assistant_departments(request.user)
    else:
        departments = Department.objects.filter(is_active=True).order_by('code')

    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        title = request.POST.get('title', '').strip()
        role_description = request.POST.get('role_description', '').strip()
        job_location = request.POST.get('job_location', '').strip()
        package_ctc_str = request.POST.get('package_ctc', '').strip()
        bond_details = request.POST.get('bond_details', '').strip()

        # Cut-offs
        min_tenth_str = request.POST.get('min_tenth_percentage', '0').strip()
        min_twelfth_str = request.POST.get('min_twelfth_percentage', '0').strip()
        min_cgpa_str = request.POST.get('min_graduation_cgpa', '0').strip()
        max_backlogs_str = request.POST.get('max_active_backlogs', '0').strip()
        allowed_dept_ids = request.POST.getlist('allowed_departments')
        allowed_batches = request.POST.get('allowed_batches', '2025,2026').strip()
        allowed_degrees = request.POST.get('allowed_degrees', 'B.Tech').strip()

        deadline_str = request.POST.get('application_deadline')
        drive_date_str = request.POST.get('drive_date')

        errors = {}
        if not company_id:
            errors['company_id'] = 'Please select a hiring company.'
        if not title:
            errors['title'] = 'Job designation / title is required.'
        if not role_description:
            errors['role_description'] = 'Job description is required.'
        if not job_location:
            errors['job_location'] = 'Job location is required.'
        if not allowed_dept_ids:
            errors['allowed_departments'] = 'Please select at least one eligible department.'
        if not deadline_str:
            errors['application_deadline'] = 'Application deadline is required.'
        if not drive_date_str:
            errors['drive_date'] = 'Drive date is required.'

        # Enforce assistant department boundaries
        if request.user.role == UserRole.TNP_ASSISTANT:
            allowed_dept_ids = [str(d.id) for d in departments if str(d.id) in allowed_dept_ids]
            if not allowed_dept_ids:
                errors['allowed_departments'] = 'You can only post job openings for your assigned department(s).'

        try:
            package_ctc = Decimal(package_ctc_str)
            if package_ctc <= 0:
                errors['package_ctc'] = 'Package must be greater than 0 LPA.'
        except (InvalidOperation, ValueError):
            errors['package_ctc'] = 'Invalid compensation format (must be e.g. 12.50).'

        try:
            min_tenth = Decimal(min_tenth_str)
            min_twelfth = Decimal(min_twelfth_str)
            min_cgpa = Decimal(min_cgpa_str)
            max_backlogs = int(max_backlogs_str)
        except (InvalidOperation, ValueError):
            errors['cutoffs'] = 'Invalid cut-off numeric parameters.'

        if errors:
            return render(request, 'placements/post_job.html', {
                'errors': errors,
                'form_data': request.POST,
                'companies': companies,
                'departments': departments,
                'selected_dept_ids': [int(i) for i in allowed_dept_ids if i.isdigit()],
                'active_nav': 'post_job'
            })

        company = get_object_or_404(Company, id=company_id)
        job = JobOpening.objects.create(
            company=company,
            title=title,
            role_description=role_description,
            job_location=job_location,
            package_ctc=package_ctc,
            bond_details=bond_details,
            min_tenth_percentage=min_tenth,
            min_twelfth_percentage=min_twelfth,
            min_graduation_cgpa=min_cgpa,
            max_active_backlogs=max_backlogs,
            allowed_degrees=allowed_degrees,
            allowed_batches=allowed_batches,
            application_deadline=deadline_str,
            drive_date=drive_date_str,
            created_by=request.user,
            status=JobStatus.PUBLISHED
        )

        # Set allowed departments and create department approvals
        selected_depts = Department.objects.filter(id__in=allowed_dept_ids)
        job.allowed_departments.set(selected_depts)

        for dept in selected_depts:
            if request.user.role == UserRole.TNP_ASSISTANT:
                DepartmentJobApproval.objects.create(
                    job_opening=job,
                    department=dept,
                    status=ApprovalStatus.APPROVED,
                    reviewed_by=request.user,
                    reviewed_at=timezone.now(),
                    comments="Directly posted and verified by Department TnP Assistant."
                )
            else:
                DepartmentJobApproval.objects.create(
                    job_opening=job,
                    department=dept,
                    status=ApprovalStatus.PENDING
                )

        # Notification broadcast for students
        Notification.objects.create(
            target_role='STUDENT',
            title=f"New Campus Drive: {company.name} ({title})",
            message=f"{company.name} announced a drive for {title} offering {package_ctc} LPA. Check eligibility now!",
            action_url=f"/student/jobs/"
        )

        AuditLog.objects.create(
            user=request.user,
            action="POST_JOB_OPENING",
            entity_type="JobOpening",
            entity_id=str(job.id),
            details=f"Posted campus drive: {title} at {company.name} ({package_ctc} LPA)"
        )

        messages.success(request, f"Drive for {title} at {company.name} published successfully.")
        return redirect('placements:drive_detail', job_id=job.id)

    return render(request, 'placements/post_job.html', {
        'companies': companies,
        'departments': departments,
        'active_nav': 'post_job',
        'form_data': {},
        'errors': {},
        'selected_dept_ids': [],
    })


@role_required(['TNP_OFFICER', 'ADMIN'])
def job_edit_view(request, job_id):
    """
    Edits an existing placement drive parameters and recruitment lifecycle status.
    """
    job = get_object_or_404(
        JobOpening.objects.select_related('company').prefetch_related('allowed_departments'),
        id=job_id
    )

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        role_description = request.POST.get('role_description', '').strip()
        job_location = request.POST.get('job_location', '').strip()
        package_ctc_str = request.POST.get('package_ctc', '').strip()
        bond_details = request.POST.get('bond_details', '').strip()
        status = request.POST.get('status', job.status)
        deadline_str = request.POST.get('application_deadline')
        drive_date_str = request.POST.get('drive_date')

        errors = {}
        if not title:
            errors['title'] = 'Title is required.'
        if not role_description:
            errors['role_description'] = 'Job description is required.'

        try:
            package_ctc = Decimal(package_ctc_str)
            if package_ctc <= 0:
                errors['package_ctc'] = 'Package must be greater than 0.'
        except (InvalidOperation, ValueError):
            errors['package_ctc'] = 'Invalid compensation format.'

        if errors:
            return render(request, 'placements/job_edit.html', {
                'job': job,
                'errors': errors,
                'statuses': JobStatus.choices,
                'active_nav': 'drives'
            })

        old_status = job.status
        job.title = title
        job.role_description = role_description
        job.job_location = job_location
        job.package_ctc = package_ctc
        job.bond_details = bond_details
        job.status = status
        if deadline_str:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(deadline_str.replace('T', ' '))
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            job.application_deadline = dt if dt else deadline_str
        if drive_date_str:
            job.drive_date = drive_date_str
        job.save()

        # If drive is cancelled, issue notification to all candidates who applied
        if old_status != JobStatus.CANCELLED and status == JobStatus.CANCELLED:
            for app in job.applications.select_related('student__user'):
                Notification.objects.create(
                    recipient=app.student.user,
                    title=f"Drive Cancelled: {job.title} ({job.company.name})",
                    message=f"The campus recruitment drive for {job.title} at {job.company.name} has been officially cancelled.",
                    action_url="/student/applications/"
                )

        AuditLog.objects.create(
            user=request.user,
            action="UPDATE_JOB_OPENING",
            entity_type="JobOpening",
            entity_id=str(job.id),
            details=f"Updated job {job.title} at {job.company.name} (Status: {old_status} -> {status})"
        )

        messages.success(request, f"Drive '{job.title}' updated successfully.")
        return redirect('placements:drive_detail', job_id=job.id)

    return render(request, 'placements/job_edit.html', {
        'job': job,
        'statuses': JobStatus.choices,
        'active_nav': 'drives'
    })
