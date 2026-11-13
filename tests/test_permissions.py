from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from apps.accounts.models import User, UserRole
from apps.departments.models import Department
from apps.students.models import StudentProfile


class RolePermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(code='CSE', name='Computer Science')

        self.admin = User.objects.create_user(
            email='admin@apex.edu.in',
            password='Password@123',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN
        )
        self.student = User.objects.create_user(
            email='student@apex.edu.in',
            password='Password@123',
            first_name='Student',
            last_name='User',
            role=UserRole.STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            department=self.dept,
            roll_number='21CSE000',
            prn_number='PRN000',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('80.00'),
            twelfth_percentage=Decimal('80.00'),
            graduation_cgpa=Decimal('8.00')
        )
        self.tpo = User.objects.create_user(
            email='tpo@apex.edu.in',
            password='Password@123',
            first_name='TPO',
            last_name='User',
            role=UserRole.TNP_OFFICER
        )

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated requests to protected dashboards must redirect to login."""
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_student_cannot_access_admin_panel(self):
        """Students must be denied access to administrative endpoints."""
        self.client.force_login(self.student)
        response = self.client.get(reverse('admin_panel:dashboard'))
        # Should redirect to student's own dashboard
        self.assertRedirects(response, reverse('student_panel:dashboard'))

    def test_student_cannot_access_tpo_panel(self):
        """Students cannot access TPO dashboard."""
        self.client.force_login(self.student)
        response = self.client.get(reverse('tpo_panel:dashboard'))
        self.assertRedirects(response, reverse('student_panel:dashboard'))

    def test_tpo_cannot_access_admin_users_list(self):
        """TPO cannot access user provisioning in Admin panel."""
        self.client.force_login(self.tpo)
        response = self.client.get(reverse('admin_panel:users'))
        self.assertRedirects(response, reverse('tpo_panel:dashboard'))

    def test_admin_can_access_admin_panel(self):
        """Admin can access admin panel."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
