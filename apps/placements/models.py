from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.companies.models import Company
from apps.departments.models import Department


class JobStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published / Accepting Applications'
    IN_PROGRESS = 'IN_PROGRESS', 'Recruitment Rounds In Progress'
    COMPLETED = 'COMPLETED', 'Drive Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class ApprovalStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Department Review'
    APPROVED = 'APPROVED', 'Approved for Department'
    REJECTED = 'REJECTED', 'Rejected for Department'


class JobOpening(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='job_openings'
    )
    title = models.CharField(max_length=150, help_text="Designation (e.g. SDE 1, Graduate Engineer Trainee)")
    role_description = models.TextField()
    job_location = models.CharField(max_length=150, help_text="e.g. Bangalore, Pune, Hybrid")
    package_ctc = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Offered compensation in LPA (e.g. 14.50)"
    )
    bond_details = models.CharField(max_length=255, blank=True, null=True, help_text="e.g. No Bond, or 1 Year Service Agreement")

    # Eligibility Cut-Off Matrix
    min_tenth_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Minimum 10th standard percentage required (0.00 = No cutoff)"
    )
    min_twelfth_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Minimum 12th / Diploma percentage required (0.00 = No cutoff)"
    )
    min_graduation_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        help_text="Minimum CGPA required on 10.0 scale (0.00 = No cutoff)"
    )
    max_active_backlogs = models.PositiveIntegerField(
        default=0,
        help_text="Maximum allowed live backlogs (e.g. 0)"
    )
    allowed_departments = models.ManyToManyField(
        Department,
        related_name='eligible_job_openings',
        help_text="Academic branches allowed to apply"
    )
    allowed_degrees = models.CharField(
        max_length=255,
        default='B.Tech',
        help_text="Comma-separated degrees (e.g. B.Tech, M.Tech, MCA)"
    )
    allowed_batches = models.CharField(
        max_length=100,
        default='2025,2026',
        help_text="Comma-separated graduation batch years (e.g. 2025, 2026)"
    )

    application_deadline = models.DateTimeField(help_text="Cut-off date & time for student applications")
    drive_date = models.DateField(help_text="Scheduled date for on-campus / virtual drive")
    status = models.CharField(
        max_length=30,
        choices=JobStatus.choices,
        default=JobStatus.PUBLISHED,
        db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_job_openings'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job Opening"
        verbose_name_plural = "Job Openings"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.company.name} ({self.package_ctc} LPA)"

    @property
    def is_deadline_passed(self):
        return timezone.now() > self.application_deadline

    @property
    def total_applicants_count(self):
        return self.applications.count()

    @property
    def total_placed_count(self):
        return self.applications.filter(stage='OFFERED').count()


class DepartmentJobApproval(models.Model):
    job_opening = models.ForeignKey(
        JobOpening,
        on_delete=models.CASCADE,
        related_name='department_approvals'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='job_opening_approvals'
    )
    status = models.CharField(
        max_length=30,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_reviews_conducted'
    )
    comments = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Department Job Approval"
        verbose_name_plural = "Department Job Approvals"
        unique_together = ('job_opening', 'department')

    def __str__(self):
        return f"{self.job_opening.title} - {self.department.code}: {self.get_status_display()}"
