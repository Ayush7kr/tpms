from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.departments.models import Department
from apps.placements.models import JobOpening


class ResourceCategory(models.TextChoices):
    APTITUDE = 'APTITUDE', 'Quantitative Aptitude & Logical Reasoning'
    TECHNICAL_CODING = 'TECHNICAL_CODING', 'Data Structures, Algorithms & Coding'
    CORE_ENGINEERING = 'CORE_ENGINEERING', 'Core Branch Concepts & Gate Prep'
    HR_INTERVIEW = 'HR_INTERVIEW', 'HR Interview, Behavioral & Soft Skills'
    RESUME_BUILDING = 'RESUME_BUILDING', 'Resume Formats, Cover Letters & Portfolio'


class ResourceType(models.TextChoices):
    DOCUMENT_FILE = 'DOCUMENT_FILE', 'PDF / Document Attachment'
    VIDEO_LINK = 'VIDEO_LINK', 'Video Lecture / Workshop'
    EXTERNAL_URL = 'EXTERNAL_URL', 'External Tutorial / Practice Link'


class StudyMaterial(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=50,
        choices=ResourceCategory.choices,
        default=ResourceCategory.TECHNICAL_CODING,
        db_index=True
    )
    resource_type = models.CharField(
        max_length=30,
        choices=ResourceType.choices,
        default=ResourceType.DOCUMENT_FILE
    )
    file_attachment = models.FileField(
        upload_to='study_materials/',
        blank=True,
        null=True,
        help_text="PDF or Document file"
    )
    external_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="YouTube, Drive link or web article"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='study_materials',
        help_text="Leave blank if resource is relevant across all departments"
    )
    job_opening = models.ForeignKey(
        JobOpening,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='study_materials',
        help_text="Tag directly to a specific company drive if applicable"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_materials'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Study Material"
        verbose_name_plural = "Study Materials"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"
