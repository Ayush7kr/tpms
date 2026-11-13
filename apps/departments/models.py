from django.db import models
from django.conf import settings
from django.utils import timezone


class Department(models.Model):
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Standard department code (e.g., CSE, IT, ECE, MECH, CIVIL)"
    )
    name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Full department name (e.g., Computer Science and Engineering)"
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def active_student_count(self):
        return self.students.filter(user__is_active=True).count()

    def placed_student_count(self):
        return self.students.filter(placement_status='PLACED').count()


class AssistantDepartmentAssignment(models.Model):
    assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_departments',
        limit_choices_to={'role': 'TNP_ASSISTANT'}
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='assigned_assistants'
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='department_assignments_made'
    )

    class Meta:
        verbose_name = "Assistant Department Assignment"
        verbose_name_plural = "Assistant Department Assignments"
        unique_together = ('assistant', 'department')

    def __str__(self):
        return f"{self.assistant.get_full_name()} -> {self.department.code}"
