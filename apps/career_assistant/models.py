from django.db import models
from django.utils import timezone
from apps.students.models import StudentProfile


class Conversation(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='career_conversations'
    )
    title = models.CharField(max_length=200, default='New Career Chat')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.student.roll_number})"


class ChatMessage(models.Model):
    SENDER_CHOICES = [
        ('STUDENT', 'Student'),
        ('ASSISTANT', 'Career Assistant'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.sender}] {self.content[:40]}"
