from django.conf import settings


def unread_notifications_for(user):
    """Notifications addressed to this user, or broadcast to their role, that they haven't read."""
    from django.db.models import Q
    from apps.notifications.models import Notification
    return (
        Notification.objects.filter(Q(recipient=user, is_read=False) | Q(recipient__isnull=True, target_role=user.role))
        .exclude(read_by=user)
    )


def tpms_global_context(request):
    unread = 0
    if request.user.is_authenticated:
        try:
            unread = unread_notifications_for(request.user).count()
        except Exception:
            unread = 0

    return {
        'INSTITUTE_NAME': settings.INSTITUTE_NAME,
        'INSTITUTE_SHORT_NAME': settings.INSTITUTE_SHORT_NAME,
        'SYSTEM_NAME': 'Training & Placement Cell',
        'CURRENT_ACADEMIC_YEAR': settings.CURRENT_ACADEMIC_YEAR,
        'UNREAD_NOTIFICATIONS_COUNT': unread,
        'DEMO_MODE': settings.DEMO_MODE,
    }
