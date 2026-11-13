from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.urls import reverse


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrator'
    PRINCIPAL = 'PRINCIPAL', 'Principal'
    TNP_OFFICER = 'TNP_OFFICER', 'TnP Officer'
    TNP_ASSISTANT = 'TNP_ASSISTANT', 'TnP Assistant'
    STUDENT = 'STUDENT', 'Student'


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('An email address is required to register.')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name='Email Address',
        max_length=255,
        unique=True,
        db_index=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email}) - {self.get_role_display()}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_principal(self):
        return self.role == UserRole.PRINCIPAL

    @property
    def is_tnp_officer(self):
        return self.role == UserRole.TNP_OFFICER

    @property
    def is_tnp_assistant(self):
        return self.role == UserRole.TNP_ASSISTANT

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    def get_dashboard_url(self):
        """Dispatches user to their designated dashboard route based on role."""
        if self.role == UserRole.ADMIN:
            return reverse('admin_panel:dashboard')
        elif self.role == UserRole.PRINCIPAL:
            return reverse('principal_panel:dashboard')
        elif self.role == UserRole.TNP_OFFICER:
            return reverse('tpo_panel:dashboard')
        elif self.role == UserRole.TNP_ASSISTANT:
            return reverse('assistant_panel:dashboard')
        elif self.role == UserRole.STUDENT:
            return reverse('student_panel:dashboard')
        return reverse('core:landing')
