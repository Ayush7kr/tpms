from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Direct recipient. If NULL, broadcast to role."
    )
    target_role = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        db_index=True,
        help_text="If set, all users with this role will see this announcement"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        target = self.recipient.email if self.recipient else f"Role: {self.target_role}"
        return f"[{target}] {self.title}"
