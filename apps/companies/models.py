from django.db import models
from django.utils import timezone


class CompanyTier(models.TextChoices):
    TIER_1_DREAM = 'TIER_1_DREAM', 'Dream (12+ LPA)'
    TIER_2_CORE = 'TIER_2_CORE', 'Core (6-12 LPA)'
    TIER_3_MASS = 'TIER_3_MASS', 'Mass (under 6 LPA)'


class Company(models.Model):
    name = models.CharField(max_length=150, unique=True, db_index=True)
    website = models.URLField(blank=True, null=True)
    industry_sector = models.CharField(max_length=100, help_text="e.g. Information Technology, FinTech, Automotive")
    tier = models.CharField(
        max_length=30,
        choices=CompanyTier.choices,
        default=CompanyTier.TIER_2_CORE
    )
    contact_person = models.CharField(max_length=100, help_text="Recruiter / HR Point of Contact")
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name

    def active_openings_count(self):
        return self.job_openings.filter(status='PUBLISHED').count()

    def total_hires_count(self):
        return self.hired_students.count()
