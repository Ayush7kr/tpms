from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Q
from apps.accounts.models import User, UserRole
from apps.accounts.decorators import login_required_custom
from apps.notifications.models import Notification
from apps.audit.models import AuditLog


ROLES_METADATA = {
    'STUDENT': {
        'code': 'STUDENT',
        'title': 'Student Portal',
        'badge': 'Student Candidate',
        'badge_class': 'success',
        'icon': 'bi-mortarboard-fill',
        'description': 'Explore eligible campus drives, apply with 1-click, track interview rounds & study materials.',
        'placeholder': 'e.g. 21cse001@apex.edu.in or email',
        'demo_email': 'aarav.mehta@apex.edu.in',
        'demo_name': 'Aarav Mehta (B.Tech CSE - Eligible)',
        'accent_color': '#10b981',
    },
    'TNP_OFFICER': {
        'code': 'TNP_OFFICER',
        'title': 'T&P Officer Portal',
        'badge': 'Placement Directorate',
        'badge_class': 'primary',
        'icon': 'bi-briefcase-fill',
        'description': 'Post campus drives, manage corporate partners, review branch approvals & track central hiring pipeline.',
        'placeholder': 'e.g. tpo@apex.edu.in',
        'demo_email': 'tpo@apex.edu.in',
        'demo_name': 'Prof. Vikram Malhotra (TPO)',
        'accent_color': '#2563eb',
    },
    'TNP_ASSISTANT': {
        'code': 'TNP_ASSISTANT',
        'title': 'TnP Assistant Portal',
        'badge': 'Department Coordinator',
        'badge_class': 'info',
        'icon': 'bi-diagram-3-fill',
        'description': 'Verify student profiles & resumes, review branch-specific job drives, & maintain department roster.',
        'placeholder': 'e.g. assistant.cse@apex.edu.in',
        'demo_email': 'assistant.cse@apex.edu.in',
        'demo_name': 'Ananya Deshmukh (CSE Assistant)',
        'accent_color': '#06b6d4',
    },
    'PRINCIPAL': {
        'code': 'PRINCIPAL',
        'title': 'Principal & Director Portal',
        'badge': 'Executive Oversight',
        'badge_class': 'warning',
        'icon': 'bi-speedometer2',
        'description': 'Executive placement KPI dashboard, department-wise analytics, cut-off queries & CSV reporting.',
        'placeholder': 'e.g. principal@apex.edu.in',
        'demo_email': 'principal@apex.edu.in',
        'demo_name': 'Dr. Rajesh Sharma (Principal)',
        'accent_color': '#f59e0b',
    },
    'ADMIN': {
        'code': 'ADMIN',
        'title': 'System Administrator Portal',
        'badge': 'IT Governance & Master Control',
        'badge_class': 'danger',
        'icon': 'bi-shield-lock-fill',
        'description': 'Master user accounts, academic departments, assistant allocations & chronological audit trails.',
        'placeholder': 'e.g. admin@apex.edu.in',
        'demo_email': 'admin@apex.edu.in',
        'demo_name': 'System Administrator',
        'accent_color': '#ef4444',
    },
}


def normalize_role(role_str):
    if not role_str:
        return ''
    r = role_str.strip().upper()
    if r in ('TPO', 'OFFICER', 'TNP_OFFICER'):
        return UserRole.TNP_OFFICER
    if r in ('ASSISTANT', 'ASST', 'TNP_ASSISTANT'):
        return UserRole.TNP_ASSISTANT
    if r in ('ADMIN', 'ADMINISTRATOR'):
        return UserRole.ADMIN
    if r in ('PRINCIPAL', 'DIRECTOR'):
        return UserRole.PRINCIPAL
    if r in ('STUDENT', 'CANDIDATE'):
        return UserRole.STUDENT
    return r if r in [x[0] for x in UserRole.choices] else ''


def login_view(request):
    """
    Custom institutional authentication handler.
    Authenticates by email and password, determines user role automatically from
    the database record, and dispatches to the corresponding portal dashboard.
    Strictly NO Django default authentication form.
    """
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        if not email or not password:
            return render(request, 'public/login.html', {
                'error': 'Please provide both institutional email and password.',
                'submitted_email': email,
            })

        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                return render(request, 'public/login.html', {
                    'error': 'This account has been deactivated. Please contact the institutional administrator.',
                    'submitted_email': email,
                })

            login(request, user)

            # Session expiration handling
            if not remember_me:
                request.session.set_expiry(0)  # Browser session only

            # Audit log login event
            try:
                AuditLog.objects.create(
                    user=user,
                    action="USER_LOGIN",
                    entity_type="User",
                    entity_id=str(user.id),
                    details=f"Successful sign-in to {user.get_role_display()} portal."
                )
            except Exception:
                pass

            messages.success(request, f"Welcome back, {user.get_full_name()}!")

            # Safe redirect to next parameter if valid, else designated role dashboard
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(user.get_dashboard_url())
        else:
            return render(request, 'public/login.html', {
                'error': 'Invalid credentials. Please verify your institutional email and password.',
                'submitted_email': email,
            })

    return render(request, 'public/login.html', {
        'submitted_email': request.GET.get('email', ''),
    })


def logout_view(request):
    """
    Terminates user session and redirects to public landing page.
    """
    logout(request)
    messages.info(request, "You have been safely signed out.")
    return redirect('core:landing')


def role_redirect_view(request):
    """
    Dispatches authenticated user to their role-specific dashboard.
    """
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    return redirect('accounts:login')


def quick_switch_view(request, role):
    """
    DEMONSTRATION TOOL: Allows instant 1-click role switching for project mentor evaluation.
    """
    valid_roles = [r[0] for r in UserRole.choices]
    if role not in valid_roles:
        messages.error(request, "Invalid role requested for demonstration switch.")
        return redirect('accounts:login')

    target_user = User.objects.filter(role=role, is_active=True).first()
    if not target_user:
        messages.warning(request, f"No active user found with role {role}. Please ensure database is seeded.")
        return redirect('accounts:login')

    # Switch session to target user
    login(request, target_user)
    messages.success(request, f"Switched to [{target_user.get_role_display()}] view as {target_user.get_full_name()}.")
    return redirect(target_user.get_dashboard_url())


@login_required_custom
def notifications_view(request):
    """
    Lists notifications for the authenticated user and allows marking as read.
    Supports both direct user notifications and role-based broadcasts.
    """
    user_notifications = Notification.objects.filter(
        Q(recipient=request.user) | Q(target_role=request.user.role)
    )

    if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
        Notification.objects.filter(recipient=request.user).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('accounts:notifications')

    return render(request, 'base/notifications.html', {
        'notifications': user_notifications.order_by('-created_at')[:50],
        'active_nav': 'notifications'
    })


@login_required_custom
def change_password_view(request):
    """
    Self-service password update handler.
    Strictly custom HTML form, zero Django default auth forms.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = {}
        if not current_password:
            errors['current_password'] = 'Current password is required.'
        elif not request.user.check_password(current_password):
            errors['current_password'] = 'Current password is incorrect.'

        if not new_password:
            errors['new_password'] = 'New password is required.'
        elif len(new_password) < 8:
            errors['new_password'] = 'New password must be at least 8 characters long.'

        if new_password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'

        if errors:
            return render(request, 'accounts/change_password.html', {
                'errors': errors,
                'active_nav': 'change_password'
            })

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        AuditLog.objects.create(
            user=request.user,
            action="CHANGE_PASSWORD",
            entity_type="User",
            entity_id=str(request.user.id),
            details="User updated personal account password."
        )

        messages.success(request, "Your password has been changed successfully.")
        return redirect(request.user.get_dashboard_url())

    return render(request, 'accounts/change_password.html', {
        'active_nav': 'change_password'
    })
