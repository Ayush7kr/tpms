from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def login_required_custom(view_func):
    """
    Ensures that the client has an active, authenticated user session.
    Immediately evicts deactivated or disabled accounts.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this resource.")
            return redirect('accounts:login')

        if not request.user.is_active:
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, "Your account has been deactivated. Please contact the administrator.")
            return redirect('accounts:login')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles):
    """
    Restricts access to specific role(s). If unauthenticated or deactivated, redirects to login.
    If unauthorized, warns the user and redirects to their role dashboard.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Authentication required.")
                return redirect('accounts:login')

            if not request.user.is_active:
                from django.contrib.auth import logout
                logout(request)
                messages.error(request, "Your account has been deactivated. Please contact the administrator.")
                return redirect('accounts:login')

            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, f"Access Restricted: Your role ({request.user.get_role_display()}) cannot access this section.")
                return redirect(request.user.get_dashboard_url())

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    return role_required(['ADMIN'])(view_func)


def principal_required(view_func):
    return role_required(['PRINCIPAL', 'ADMIN'])(view_func)


def tpo_required(view_func):
    return role_required(['TNP_OFFICER', 'ADMIN'])(view_func)


def assistant_required(view_func):
    return role_required(['TNP_ASSISTANT', 'ADMIN'])(view_func)


def student_required(view_func):
    return role_required(['STUDENT'])(view_func)


def get_user_department_ids(user):
    """
    Returns list of department IDs accessible by this user.
    - ADMIN, PRINCIPAL, TNP_OFFICER have access across all departments.
    - TNP_ASSISTANT is restricted to assigned departments.
    - STUDENT is restricted to their own department.
    """
    from apps.departments.models import Department
    if user.is_superuser or user.role in ['ADMIN', 'PRINCIPAL', 'TNP_OFFICER']:
        return list(Department.objects.values_list('id', flat=True))
    elif user.role == 'TNP_ASSISTANT':
        return list(user.assistant_departments.values_list('department_id', flat=True))
    elif user.role == 'STUDENT' and hasattr(user, 'student_profile'):
        return [user.student_profile.department_id]
    return []
