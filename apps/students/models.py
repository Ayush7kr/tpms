from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.departments.models import Department
from apps.companies.models import Company


class PlacementStatus(models.TextChoices):
    UNPLACED = 'UNPLACED', 'Unplaced'
    PLACED = 'PLACED', 'Placed'
    OPTED_OUT = 'OPTED_OUT', 'Opted Out'


class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='students'
    )
    roll_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Institutional Roll Number (e.g. 21CSE104)"
    )
    prn_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Permanent Registration Number (University PRN / USN)"
    )
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.MALE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    batch_year = models.IntegerField(
        db_index=True,
        help_text="Year of Passing (e.g. 2025)"
    )
    degree = models.CharField(
        max_length=50,
        default='B.Tech',
        help_text="Degree (e.g. B.Tech, M.Tech, MCA)"
    )
    tenth_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="10th Standard Board Percentage (0.00 to 100.00)"
    )
    twelfth_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="12th / Diploma Examination Percentage (0.00 to 100.00)"
    )
    graduation_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Graduation CGPA on 10.0 scale (0.00 to 10.00)"
    )
    active_backlogs = models.PositiveIntegerField(
        default=0,
        help_text="Current number of live uncleared backlogs"
    )
    history_of_backlogs = models.PositiveIntegerField(
        default=0,
        help_text="Historical total of backlogs cleared"
    )
    resume = models.FileField(
        upload_to='resumes/',
        blank=True,
        null=True,
        help_text="PDF Resume"
    )
    skills = models.TextField(
        blank=True,
        help_text="Comma-separated skills (e.g. Python, Django, SQL, React)"
    )
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)

    placement_status = models.CharField(
        max_length=30,
        choices=PlacementStatus.choices,
        default=PlacementStatus.UNPLACED,
        db_index=True
    )
    placed_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hired_students'
    )
    salary_package = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Offered annual package in LPA (e.g. 12.50)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name()} ({self.department.code})"

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def email(self):
        return self.user.email

    @property
    def phone(self):
        return self.user.phone
