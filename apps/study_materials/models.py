from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.departments.models import Department
from apps.placements.models import JobOpening


class ResourceCategory(models.TextChoices):
    APTITUDE = 'APTITUDE', 'Aptitude & reasoning'
    TECHNICAL_CODING = 'TECHNICAL_CODING', 'Coding & DSA'
    CORE_ENGINEERING = 'CORE_ENGINEERING', 'Core subjects'
    HR_INTERVIEW = 'HR_INTERVIEW', 'HR & behavioural'
    RESUME_BUILDING = 'RESUME_BUILDING', 'Resume & portfolio'


class ResourceType(models.TextChoices):
    DOCUMENT_FILE = 'DOCUMENT_FILE', 'Document'
    VIDEO_LINK = 'VIDEO_LINK', 'Video'
    EXTERNAL_URL = 'EXTERNAL_URL', 'Link'


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
