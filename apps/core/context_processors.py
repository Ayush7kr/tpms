def tpms_global_context(request):
    """
    Supplies global institutional configuration and active user status to all templates.
    """
    unread_notifications_count = 0
    if request.user.is_authenticated:
        try:
            from django.db.models import Q
            from apps.notifications.models import Notification
            # Notifications specifically for user or for their role
            unread_notifications_count = Notification.objects.filter(
                is_read=False
            ).filter(
                Q(recipient=request.user) | Q(target_role=request.user.role)
            ).count()
        except Exception:
            unread_notifications_count = 0

    return {
        'INSTITUTE_NAME': 'Apex Institute of Technology',
        'INSTITUTE_SHORT_NAME': 'AIT',
        'SYSTEM_NAME': 'Training & Placement Management System',
        'CURRENT_ACADEMIC_YEAR': '2025-2026',
        'UNREAD_NOTIFICATIONS_COUNT': unread_notifications_count,
    }
