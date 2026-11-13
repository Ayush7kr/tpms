from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.accounts.decorators import admin_required
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile
from apps.placements.models import JobOpening
from apps.audit.models import AuditLog


@admin_required
def dashboard_view(request):
    """
    Central Admin Dashboard displaying system-wide counts and placement overview.
    """
    total_users = User.objects.count()
    total_departments = Department.objects.count()
    total_students = StudentProfile.objects.count()
    placed_students = StudentProfile.objects.filter(placement_status='PLACED').count()
    active_job_openings = JobOpening.objects.filter(status='PUBLISHED').count()

    # Department-wise student breakdown
    dept_stats = Department.objects.annotate(
        student_count=Count('students'),
        placed_count=Count('students', filter=Q(students__placement_status='PLACED'))
    )

    recent_users = User.objects.exclude(id=request.user.id).order_by('-date_joined')[:6]
    recent_audit = AuditLog.objects.order_by('-created_at')[:6]

    return render(request, 'admin_panel/dashboard.html', {
        'total_users': total_users,
        'total_departments': total_departments,
        'total_students': total_students,
        'placed_students': placed_students,
        'active_job_openings': active_job_openings,
        'dept_stats': dept_stats,
        'recent_users': recent_users,
        'recent_audit': recent_audit,
        'active_nav': 'dashboard'
    })


@admin_required
def users_list_view(request):
    """
    Lists system users with filtering by role, multi-field search, and pagination.
    """
    role_filter = request.GET.get('role', '')
    query = request.GET.get('q', '').strip()

    users_qs = User.objects.all().order_by('-date_joined')

    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if query:
        users_qs = users_qs.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    paginator = Paginator(users_qs, 15)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(request, 'admin_panel/users_list.html', {
        'users': users,
        'selected_role': role_filter,
        'query': query,
        'roles': UserRole.choices,
        'total_count': users_qs.count(),
        'active_nav': 'users'
    })


@admin_required
def user_create_view(request):
    """
    Creates a new staff or student user account with manual server-side validation.
    Strictly NO Django Forms or ModelForms.
    """
    departments = Department.objects.filter(is_active=True)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        errors = {}
        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not last_name:
            errors['last_name'] = 'Last name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'A user with this email address already exists.'

        valid_roles = [r[0] for r in UserRole.choices]
        if role not in valid_roles:
            errors['role'] = 'Please select a valid role.'

        if not password or len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters long.'

        if errors:
            return render(request, 'admin_panel/user_form.html', {
                'errors': errors,
                'form_data': request.POST,
                'roles': UserRole.choices,
                'is_create': True,
                'active_nav': 'users'
            })

        # Create user
        new_user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone=phone
        )

        AuditLog.objects.create(
            user=request.user,
            action="CREATE_USER",
            entity_type="User",
            entity_id=str(new_user.id),
            details=f"Created {role} account for {new_user.get_full_name()} ({email})"
        )

        messages.success(request, f"User {new_user.get_full_name()} successfully created.")
        return redirect('admin_panel:users')

    return render(request, 'admin_panel/user_form.html', {
        'roles': UserRole.choices,
        'is_create': True,
        'active_nav': 'users',
        'user_obj': None,
        'form_data': {},
        'errors': {},
    })


@admin_required
def user_edit_view(request, user_id):
    """
    Edits an existing user account with manual validation.
    """
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        role = request.POST.get('role', '').strip()
        phone = request.POST.get('phone', '').strip()
        new_password = request.POST.get('password', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not last_name:
            errors['last_name'] = 'Last name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exclude(id=user_obj.id).exists():
            errors['email'] = 'Another user already exists with this email.'

        if errors:
            return render(request, 'admin_panel/user_form.html', {
                'errors': errors,
                'user_obj': user_obj,
                'roles': UserRole.choices,
                'is_create': False,
                'active_nav': 'users'
            })

        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.email = email
        user_obj.role = role
        user_obj.phone = phone
        user_obj.is_active = is_active

        if new_password:
            if len(new_password) < 8:
                messages.error(request, "Password was not changed: Must be at least 8 characters.")
            else:
                user_obj.set_password(new_password)

        user_obj.save()

        AuditLog.objects.create(
            user=request.user,
            action="UPDATE_USER",
            entity_type="User",
            entity_id=str(user_obj.id),
            details=f"Updated account details for {user_obj.get_full_name()} ({user_obj.email})"
        )

        messages.success(request, f"Updated account for {user_obj.get_full_name()}.")
        return redirect('admin_panel:users')

    return render(request, 'admin_panel/user_form.html', {
        'user_obj': user_obj,
        'roles': UserRole.choices,
        'is_create': False,
        'active_nav': 'users'
    })


@admin_required
def user_toggle_status_view(request, user_id):
    """
    Toggles user active / inactive status.
    """
    user_obj = get_object_or_404(User, id=user_id)
    if user_obj.id == request.user.id:
        messages.error(request, "You cannot deactivate your own administrative account.")
        return redirect('admin_panel:users')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status_str = "activated" if user_obj.is_active else "deactivated"
    AuditLog.objects.create(
        user=request.user,
        action="TOGGLE_USER_STATUS",
        entity_type="User",
        entity_id=str(user_obj.id),
        details=f"User {user_obj.email} was {status_str}"
    )

    messages.info(request, f"Account {user_obj.email} was {status_str}.")
    return redirect('admin_panel:users')


@admin_required
def user_delete_view(request, user_id):
    """
    Deletes a user account with strict administrative safeguards.
    """
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if user_obj.id == request.user.id:
            messages.error(request, "You cannot delete your own administrative account.")
            return redirect('admin_panel:users')

        if user_obj.role == UserRole.ADMIN:
            admin_count = User.objects.filter(role=UserRole.ADMIN, is_active=True).count()
            if admin_count <= 1:
                messages.error(request, "Cannot delete the last active Administrator account.")
                return redirect('admin_panel:users')

        name = user_obj.get_full_name()
        email = user_obj.email
        role = user_obj.role
        user_obj.delete()

        AuditLog.objects.create(
            user=request.user,
            action="DELETE_USER",
            entity_type="User",
            details=f"Deleted {role} account for {name} ({email})"
        )

        messages.success(request, f"User account {name} ({email}) has been permanently deleted.")
        return redirect('admin_panel:users')

    return redirect('admin_panel:users')


@admin_required
def departments_list_view(request):
    """
    Lists all academic branches with statistics and status.
    """
    departments = Department.objects.annotate(
        students_total=Count('students'),
        assistants_total=Count('assigned_assistants')
    ).order_by('code')

    return render(request, 'admin_panel/departments_list.html', {
        'departments': departments,
        'active_nav': 'departments'
    })


@admin_required
def department_create_view(request):
    """
    Creates a new academic department with manual validation.
    """
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        errors = {}
        if not code:
            errors['code'] = 'Department code is required (e.g. CSE).'
        elif Department.objects.filter(code=code).exists():
            errors['code'] = 'A department with this code already exists.'

        if not name:
            errors['name'] = 'Department name is required.'
        elif Department.objects.filter(name=name).exists():
            errors['name'] = 'A department with this name already exists.'

        if errors:
            return render(request, 'admin_panel/department_form.html', {
                'errors': errors,
                'form_data': request.POST,
                'is_create': True,
                'active_nav': 'departments'
            })

        dept = Department.objects.create(
            code=code,
            name=name,
            description=description
        )

        AuditLog.objects.create(
            user=request.user,
            action="CREATE_DEPARTMENT",
            entity_type="Department",
            entity_id=str(dept.id),
            details=f"Created department {code} - {name}"
        )

        messages.success(request, f"Department {dept.code} successfully created.")
        return redirect('admin_panel:departments')

    return render(request, 'admin_panel/department_form.html', {
        'is_create': True,
        'active_nav': 'departments',
        'dept': None,
        'form_data': {},
        'errors': {},
    })


@admin_required
def department_edit_view(request, dept_id):
    """
    Edits department details.
    """
    dept = get_object_or_404(Department, id=dept_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not code:
            errors['code'] = 'Department code is required.'
        elif Department.objects.filter(code=code).exclude(id=dept.id).exists():
            errors['code'] = 'Another department already uses this code.'

        if not name:
            errors['name'] = 'Department name is required.'
        elif Department.objects.filter(name=name).exclude(id=dept.id).exists():
            errors['name'] = 'Another department already uses this name.'

        if errors:
            return render(request, 'admin_panel/department_form.html', {
                'errors': errors,
                'dept': dept,
                'is_create': False,
                'active_nav': 'departments'
            })

        dept.code = code
        dept.name = name
        dept.description = description
        dept.is_active = is_active
        dept.save()

        AuditLog.objects.create(
            user=request.user,
            action="UPDATE_DEPARTMENT",
            entity_type="Department",
            entity_id=str(dept.id),
            details=f"Updated department {code} - {name}"
        )

        messages.success(request, f"Updated department {dept.code}.")
        return redirect('admin_panel:departments')

    return render(request, 'admin_panel/department_form.html', {
        'dept': dept,
        'is_create': False,
        'active_nav': 'departments'
    })


@admin_required
def department_delete_view(request, dept_id):
    """
    Deletes an academic department with relational integrity safeguards.
    """
    dept = get_object_or_404(Department, id=dept_id)

    if request.method == 'POST':
        student_count = dept.students.count()
        if student_count > 0:
            messages.error(request, f"Cannot delete department {dept.code}: It currently has {student_count} registered student records. Deactivate the department instead.")
            return redirect('admin_panel:departments')

        if dept.eligible_job_openings.exists():
            messages.error(request, f"Cannot delete department {dept.code}: It is linked to active or historical placement drives. Deactivate the department instead.")
            return redirect('admin_panel:departments')

        code = dept.code
        name = dept.name
        dept.delete()

        AuditLog.objects.create(
            user=request.user,
            action="DELETE_DEPARTMENT",
            entity_type="Department",
            details=f"Deleted department {code} - {name}"
        )

        messages.success(request, f"Department {code} ({name}) has been permanently deleted.")
        return redirect('admin_panel:departments')

    return redirect('admin_panel:departments')


@admin_required
def assistant_assignments_view(request):
    """
    Manages allocations of TnP Assistants to academic departments.
    """
    assistants = User.objects.filter(role=UserRole.TNP_ASSISTANT, is_active=True)
    departments = Department.objects.filter(is_active=True)
    assignments = AssistantDepartmentAssignment.objects.select_related('assistant', 'department').order_by('department__code')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'assign':
            assistant_id = request.POST.get('assistant_id')
            department_id = request.POST.get('department_id')

            if not assistant_id or not department_id:
                messages.error(request, "Please select both an assistant and a department.")
            else:
                assistant = get_object_or_404(User, id=assistant_id, role=UserRole.TNP_ASSISTANT)
                dept = get_object_or_404(Department, id=department_id)

                assignment, created = AssistantDepartmentAssignment.objects.get_or_create(
                    assistant=assistant,
                    department=dept,
                    defaults={'assigned_by': request.user}
                )

                if created:
                    AuditLog.objects.create(
                        user=request.user,
                        action="ASSIGN_ASSISTANT_DEPT",
                        entity_type="AssistantDepartmentAssignment",
                        entity_id=str(assignment.id),
                        details=f"Assigned {assistant.get_full_name()} to {dept.code}"
                    )
                    messages.success(request, f"Assigned {assistant.get_full_name()} to {dept.code}.")
                else:
                    messages.info(request, f"{assistant.get_full_name()} is already assigned to {dept.code}.")

        elif action == 'remove':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(AssistantDepartmentAssignment, id=assignment_id)
            desc = str(assignment)
            assignment.delete()

            AuditLog.objects.create(
                user=request.user,
                action="REMOVE_ASSISTANT_DEPT",
                entity_type="AssistantDepartmentAssignment",
                details=f"Removed assignment {desc}"
            )
            messages.success(request, "Assignment successfully revoked.")

        return redirect('admin_panel:assistant_assignments')

    return render(request, 'admin_panel/assistant_assignments.html', {
        'assistants': assistants,
        'departments': departments,
        'assignments': assignments,
        'active_nav': 'assignments'
    })


@admin_required
def audit_logs_view(request):
    """
    Displays system traceability audit logs with action filtering, text search, and pagination.
    """
    action_filter = request.GET.get('action', '')
    query = request.GET.get('q', '').strip()

    logs_qs = AuditLog.objects.select_related('user').order_by('-created_at')

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if query:
        logs_qs = logs_qs.filter(
            Q(details__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(action__icontains=query)
        )

    paginator = Paginator(logs_qs, 25)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)

    # Unique actions for filtering dropdown
    actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')

    return render(request, 'admin_panel/audit_logs.html', {
        'logs': logs,
        'actions': actions,
        'action_filter': action_filter,
        'query': query,
        'total_count': logs_qs.count(),
        'active_nav': 'audit'
    })
