from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.placements.models import JobOpening
from apps.students.models import StudentProfile


class ApplicationStage(models.TextChoices):
    APPLIED = 'APPLIED', 'Applied'
    SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
    ASSESSMENT = 'ASSESSMENT', 'Online test'
    TECHNICAL_ROUND = 'TECHNICAL_ROUND', 'Technical interview'
    HR_ROUND = 'HR_ROUND', 'HR interview'
    OFFERED = 'OFFERED', 'Offer made'
    REJECTED = 'REJECTED', 'Not selected'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'


class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Awaiting verification'
    VERIFIED = 'VERIFIED', 'Verified'
    FLAGGED = 'FLAGGED', 'Mismatch flagged'


class JobApplication(models.Model):
    job_opening = models.ForeignKey(
        JobOpening,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    applied_at = models.DateTimeField(default=timezone.now)

    # Department Assistant Verification
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications_verified'
    )
    verification_notes = models.TextField(blank=True, null=True)

    # Recruitment Stage Progression
    stage = models.CharField(
        max_length=30,
        choices=ApplicationStage.choices,
        default=ApplicationStage.APPLIED,
        db_index=True
    )
    stage_updated_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True, help_text="Notes from TPO / Recruiter regarding candidate performance")

    class Meta:
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        unique_together = ('job_opening', 'student')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student.roll_number} -> {self.job_opening.title} [{self.get_stage_display()}]"
