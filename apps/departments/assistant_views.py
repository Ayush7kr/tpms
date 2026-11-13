from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Min, Max, Q
from django.utils import timezone
from apps.accounts.decorators import assistant_required
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile, PlacementStatus, Gender
from apps.placements.models import JobOpening, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication, VerificationStatus, ApplicationStage
from apps.audit.models import AuditLog


def get_assistant_departments(user):
    """Returns queryset of departments assigned to this assistant."""
    if user.is_superuser or user.role in [UserRole.ADMIN, UserRole.PRINCIPAL, UserRole.TNP_OFFICER]:
        return Department.objects.filter(is_active=True)
    return Department.objects.filter(assigned_assistants__assistant=user, is_active=True)


@assistant_required
def dashboard_view(request):
    """
    Department-Scoped TnP Assistant Dashboard.
    Enforces multi-tenant isolation: statistics reflect only assigned branches.
    """
    assigned_depts = get_assistant_departments(request.user)

    if not assigned_depts.exists():
        return render(request, 'assistant_panel/no_assignment.html', {
            'active_nav': 'dashboard'
        })

    dept_ids = assigned_depts.values_list('id', flat=True)

    # Scoped Metrics
    dept_students = StudentProfile.objects.filter(department_id__in=dept_ids)
    total_students = dept_students.count()
    placed_students = dept_students.filter(placement_status=PlacementStatus.PLACED).count()
    unplaced_students = dept_students.filter(placement_status=PlacementStatus.UNPLACED).count()

    # Package Stats
    pkg_stats = dept_students.filter(placement_status=PlacementStatus.PLACED, salary_package__isnull=False).aggregate(
        min_pkg=Min('salary_package'),
        avg_pkg=Avg('salary_package'),
        max_pkg=Max('salary_package')
    )
    min_package = pkg_stats['min_pkg'] or 0.0
    avg_package = round(pkg_stats['avg_pkg'] or 0.0, 2)
    max_package = pkg_stats['max_pkg'] or 0.0

    # Approvals & Verifications
    pending_approvals = DepartmentJobApproval.objects.filter(
        department_id__in=dept_ids,
        status=ApprovalStatus.PENDING
    ).count()

    pending_verifications = JobApplication.objects.filter(
        student__department_id__in=dept_ids,
        verification_status=VerificationStatus.PENDING
    ).count()

    active_job_openings = JobOpening.objects.filter(
        allowed_departments__in=dept_ids,
        status='PUBLISHED'
    ).distinct().count()

    # Recent student activity
    recent_students = dept_students.select_related('user', 'department').order_by('-created_at')[:6]

    return render(request, 'assistant_panel/dashboard.html', {
        'assigned_depts': assigned_depts,
        'total_students': total_students,
        'placed_students': placed_students,
        'unplaced_students': unplaced_students,
        'min_package': min_package,
        'avg_package': avg_package,
        'max_package': max_package,
        'pending_approvals': pending_approvals,
        'pending_verifications': pending_verifications,
        'active_job_openings': active_job_openings,
        'recent_students': recent_students,
        'active_nav': 'dashboard'
    })


@assistant_required
def student_roster_view(request):
    """
    Roster of students bounded strictly to the assistant's assigned departments.
    Supports status filter, multi-field search, and pagination.
    """
    assigned_depts = get_assistant_departments(request.user)
    dept_ids = assigned_depts.values_list('id', flat=True)

    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    students_qs = StudentProfile.objects.filter(department_id__in=dept_ids).select_related('user', 'department', 'placed_company').order_by('roll_number')

    if status_filter:
        students_qs = students_qs.filter(placement_status=status_filter)
    if query:
        students_qs = students_qs.filter(
            Q(roll_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(skills__icontains=query)
        )

    paginator = Paginator(students_qs, 15)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    return render(request, 'assistant_panel/student_roster.html', {
        'students': students,
        'assigned_depts': assigned_depts,
        'selected_status': status_filter,
        'query': query,
        'total_count': students_qs.count(),
        'statuses': PlacementStatus.choices,
        'active_nav': 'students'
    })


@assistant_required
def student_create_view(request):
    """
    Manual single student onboarding for assigned department.
    Strictly NO Django Forms.
    """
    assigned_depts = get_assistant_departments(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        department_id = request.POST.get('department_id')
        roll_number = request.POST.get('roll_number', '').strip().upper()
        prn_number = request.POST.get('prn_number', '').strip().upper()
        gender = request.POST.get('gender', Gender.MALE)
        batch_year_str = request.POST.get('batch_year', '2025').strip()
        degree = request.POST.get('degree', 'B.Tech').strip()
        tenth_str = request.POST.get('tenth_percentage', '0').strip()
        twelfth_str = request.POST.get('twelfth_percentage', '0').strip()
        cgpa_str = request.POST.get('graduation_cgpa', '0').strip()
        backlogs_str = request.POST.get('active_backlogs', '0').strip()
        skills = request.POST.get('skills', '').strip()

        errors = {}
        if not first_name or not last_name:
            errors['name'] = 'Full name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'A user with this email already exists.'

        if not roll_number:
            errors['roll_number'] = 'Roll number is required.'
        elif StudentProfile.objects.filter(roll_number=roll_number).exists():
            errors['roll_number'] = 'A student with this roll number already exists.'

        if not prn_number:
            prn_number = f"PRN{roll_number}"
        elif StudentProfile.objects.filter(prn_number=prn_number).exists():
            errors['prn_number'] = 'A student with this PRN already exists.'

        if not department_id or int(department_id) not in assigned_depts.values_list('id', flat=True):
            errors['department_id'] = 'You can only enroll students into your assigned departments.'

        try:
            tenth = Decimal(tenth_str)
            twelfth = Decimal(twelfth_str)
            cgpa = Decimal(cgpa_str)
            backlogs = int(backlogs_str)
            batch_year = int(batch_year_str)
        except (InvalidOperation, ValueError):
            errors['numbers'] = 'Invalid numeric academic values.'

        if errors:
            return render(request, 'assistant_panel/student_form.html', {
                'errors': errors,
                'form_data': request.POST,
                'assigned_depts': assigned_depts,
                'genders': Gender.choices,
                'is_create': True,
                'active_nav': 'students'
            })

        user = User.objects.create_user(
            email=email,
            password='apex@123',
            first_name=first_name,
            last_name=last_name,
            role=UserRole.STUDENT,
            phone=phone
        )

        dept = get_object_or_404(Department, id=department_id)
        profile = StudentProfile.objects.create(
            user=user,
            department=dept,
            roll_number=roll_number,
            prn_number=prn_number,
            gender=gender,
            batch_year=batch_year,
            degree=degree,
            tenth_percentage=tenth,
            twelfth_percentage=twelfth,
            graduation_cgpa=cgpa,
            active_backlogs=backlogs,
            skills=skills,
            placement_status=PlacementStatus.UNPLACED
        )

        AuditLog.objects.create(
            user=request.user,
            action="CREATE_STUDENT_PROFILE",
            entity_type="StudentProfile",
            entity_id=str(profile.id),
            details=f"Enrolled student {roll_number} - {user.get_full_name()} in {dept.code}"
        )

        messages.success(request, f"Student {user.get_full_name()} ({roll_number}) enrolled successfully. Default password: apex@123")
        return redirect('assistant_panel:student_roster')

    return render(request, 'assistant_panel/student_form.html', {
        'assigned_depts': assigned_depts,
        'genders': Gender.choices,
        'is_create': True,
        'active_nav': 'students',
        'profile': None,
        'form_data': {},
        'errors': {},
    })


@assistant_required
def student_edit_view(request, student_id):
    """
    Edits candidate academic information with strict department scoping.
    """
    assigned_depts = get_assistant_departments(request.user)
    dept_ids = assigned_depts.values_list('id', flat=True)

    profile = get_object_or_404(
        StudentProfile.objects.select_related('user', 'department'),
        id=student_id,
        department_id__in=dept_ids
    )

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        tenth_str = request.POST.get('tenth_percentage', '0').strip()
        twelfth_str = request.POST.get('twelfth_percentage', '0').strip()
        cgpa_str = request.POST.get('graduation_cgpa', '0').strip()
        backlogs_str = request.POST.get('active_backlogs', '0').strip()
        skills = request.POST.get('skills', '').strip()
        placement_status = request.POST.get('placement_status', PlacementStatus.UNPLACED)

        try:
            tenth = Decimal(tenth_str)
            twelfth = Decimal(twelfth_str)
            cgpa = Decimal(cgpa_str)
            backlogs = int(backlogs_str)
        except (InvalidOperation, ValueError):
            messages.error(request, "Invalid numeric values provided.")
            return redirect('assistant_panel:student_edit', student_id=profile.id)

        profile.user.first_name = first_name
        profile.user.last_name = last_name
        profile.user.phone = phone
        profile.user.save()

        profile.tenth_percentage = tenth
        profile.twelfth_percentage = twelfth
        profile.graduation_cgpa = cgpa
        profile.active_backlogs = backlogs
        profile.skills = skills
        profile.placement_status = placement_status
        profile.save()

        messages.success(request, f"Updated profile for {profile.roll_number}.")
        return redirect('assistant_panel:student_roster')

    return render(request, 'assistant_panel/student_form.html', {
        'profile': profile,
        'assigned_depts': assigned_depts,
        'genders': Gender.choices,
        'statuses': PlacementStatus.choices,
        'is_create': False,
        'active_nav': 'students'
    })


@assistant_required
def job_approvals_view(request):
    """
    Reviews and activates/rejects campus drives specifically for the assistant's branch.
    """
    assigned_depts = get_assistant_departments(request.user)
    dept_ids = assigned_depts.values_list('id', flat=True)

    if request.method == 'POST':
        approval_id = request.POST.get('approval_id')
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '').strip()

        approval = get_object_or_404(DepartmentJobApproval, id=approval_id, department_id__in=dept_ids)
        if decision == 'APPROVED':
            approval.status = ApprovalStatus.APPROVED
            messages.success(request, f"Drive '{approval.job_opening.title}' approved for {approval.department.code}.")
        elif decision == 'REJECTED':
            approval.status = ApprovalStatus.REJECTED
            messages.warning(request, f"Drive '{approval.job_opening.title}' rejected for {approval.department.code}.")

        approval.reviewed_by = request.user
        approval.reviewed_at = timezone.now()
        approval.comments = comments
        approval.save()

        AuditLog.objects.create(
            user=request.user,
            action=f"JOB_APPROVAL_{decision}",
            entity_type="DepartmentJobApproval",
            entity_id=str(approval.id),
            details=f"{decision} drive {approval.job_opening.title} for {approval.department.code}"
        )

        return redirect('assistant_panel:job_approvals')

    approvals = DepartmentJobApproval.objects.filter(
        department_id__in=dept_ids
    ).select_related('job_opening__company', 'department', 'reviewed_by').order_by('-job_opening__created_at')

    return render(request, 'assistant_panel/job_approvals.html', {
        'approvals': approvals,
        'active_nav': 'job_approvals'
    })


@assistant_required
def verify_applications_view(request):
    """
    Verifies candidate academic records for submitted job applications.
    """
    assigned_depts = get_assistant_departments(request.user)
    dept_ids = assigned_depts.values_list('id', flat=True)

    if request.method == 'POST':
        app_id = request.POST.get('application_id')
        ver_status = request.POST.get('verification_status')
        notes = request.POST.get('verification_notes', '').strip()

        application = get_object_or_404(
            JobApplication,
            id=app_id,
            student__department_id__in=dept_ids
        )

        application.verification_status = ver_status
        application.verified_by = request.user
        application.verification_notes = notes
        application.save()

        messages.success(request, f"Application for {application.student.roll_number} updated to {application.get_verification_status_display()}.")
        return redirect('assistant_panel:verify_applications')

    applications = JobApplication.objects.filter(
        student__department_id__in=dept_ids
    ).select_related('student__user', 'student__department', 'job_opening__company').order_by('-applied_at')

    return render(request, 'assistant_panel/verify_applications.html', {
        'applications': applications,
        'verification_statuses': VerificationStatus.choices,
        'active_nav': 'verify_apps'
    })
