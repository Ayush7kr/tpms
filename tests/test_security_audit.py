from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile, PlacementStatus
from apps.companies.models import Company, CompanyTier
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication, ApplicationStage, VerificationStatus
from apps.notifications.models import Notification


class SecurityAuditTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Departments
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science')
        self.dept_ece = Department.objects.create(code='ECE', name='Electronics')

        # Users & Roles
        self.admin = User.objects.create_superuser('admin@apex.edu.in', 'Admin@123', first_name='Admin', last_name='User', role=UserRole.ADMIN)
        self.tpo = User.objects.create_user('tpo@apex.edu.in', 'Password@123', first_name='TPO', last_name='Officer', role=UserRole.TNP_OFFICER)

        self.asst_cse = User.objects.create_user('asst.cse@apex.edu.in', 'Password@123', first_name='CSE', last_name='Assistant', role=UserRole.TNP_ASSISTANT)
        AssistantDepartmentAssignment.objects.create(assistant=self.asst_cse, department=self.dept_cse)

        # Student A (CSE)
        self.user_a = User.objects.create_user('student.a@apex.edu.in', 'Password@123', first_name='Student', last_name='Alpha', role=UserRole.STUDENT)
        fake_pdf = SimpleUploadedFile("resume_a.pdf", b"%PDF-1.4 dummy content", content_type="application/pdf")
        self.student_a = StudentProfile.objects.create(
            user=self.user_a,
            department=self.dept_cse,
            roll_number='21CSE001',
            prn_number='PRN21001',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('85.00'),
            twelfth_percentage=Decimal('85.00'),
            graduation_cgpa=Decimal('8.50'),
            resume=fake_pdf
        )

        # Student B (ECE)
        self.user_b = User.objects.create_user('student.b@apex.edu.in', 'Password@123', first_name='Student', last_name='Beta', role=UserRole.STUDENT)
        fake_pdf_b = SimpleUploadedFile("resume_b.pdf", b"%PDF-1.4 dummy content b", content_type="application/pdf")
        self.student_b = StudentProfile.objects.create(
            user=self.user_b,
            department=self.dept_ece,
            roll_number='21ECE001',
            prn_number='PRN21002',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('78.00'),
            twelfth_percentage=Decimal('80.00'),
            graduation_cgpa=Decimal('7.80'),
            resume=fake_pdf_b
        )

        # Company & Drive
        self.company = Company.objects.create(name='TechCorp Global', tier=CompanyTier.TIER_1_DREAM, is_active=True)
        self.job = JobOpening.objects.create(
            company=self.company,
            title='Software Engineer',
            role_description='Full stack engineering role',
            job_location='Bangalore',
            package_ctc=Decimal('12.00'),
            min_tenth_percentage=Decimal('70.00'),
            min_twelfth_percentage=Decimal('70.00'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            allowed_degrees='B.Tech',
            allowed_batches='2025',
            application_deadline=timezone.now() + timedelta(days=30),
            drive_date=(timezone.now() + timedelta(days=40)).date(),
            created_by=self.tpo,
            status=JobStatus.PUBLISHED
        )
        self.job.allowed_departments.set([self.dept_cse, self.dept_ece])

        # Applications
        self.app_a = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student_a,
            stage=ApplicationStage.APPLIED,
            verification_status=VerificationStatus.VERIFIED
        )
        self.app_b = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student_b,
            stage=ApplicationStage.APPLIED,
            verification_status=VerificationStatus.PENDING
        )

    def test_student_cannot_view_other_student_profile(self):
        """Student Alpha cannot view Student Beta's detailed profile (HTTP 403)."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('students:detail', kwargs={'student_id': self.student_b.id}))
        self.assertEqual(response.status_code, 403)

    def test_student_can_view_own_profile(self):
        """Student Alpha can view their own profile (HTTP 200)."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('students:detail', kwargs={'student_id': self.student_a.id}))
        self.assertEqual(response.status_code, 200)

    def test_assistant_cannot_view_unassigned_dept_student_profile(self):
        """CSE Assistant cannot view ECE student detail (HTTP 403)."""
        self.client.force_login(self.asst_cse)
        response = self.client.get(reverse('students:detail', kwargs={'student_id': self.student_b.id}))
        self.assertEqual(response.status_code, 403)

    def test_assistant_can_view_assigned_dept_student_profile(self):
        """CSE Assistant can view CSE student detail (HTTP 200)."""
        self.client.force_login(self.asst_cse)
        response = self.client.get(reverse('students:detail', kwargs={'student_id': self.student_a.id}))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_download_other_student_resume(self):
        """Student Alpha cannot download Student Beta's resume file (HTTP 403)."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('students:download_resume', kwargs={'student_id': self.student_b.id}))
        self.assertEqual(response.status_code, 403)

    def test_assistant_cannot_download_unassigned_dept_resume(self):
        """CSE Assistant cannot download ECE student resume (HTTP 403)."""
        self.client.force_login(self.asst_cse)
        response = self.client.get(reverse('students:download_resume', kwargs={'student_id': self.student_b.id}))
        self.assertEqual(response.status_code, 403)

    def test_assistant_cannot_update_stage_of_unassigned_dept_student(self):
        """CSE Assistant cannot update recruitment stage of ECE student (HTTP 403)."""
        self.client.force_login(self.asst_cse)
        response = self.client.post(
            reverse('applications:update_stage', kwargs={'application_id': self.app_b.id}),
            {'stage': ApplicationStage.TECHNICAL_ROUND, 'remarks': 'Tampering attempt'}
        )
        self.assertEqual(response.status_code, 403)

    def test_assistant_can_update_stage_of_assigned_dept_student(self):
        """CSE Assistant can update recruitment stage of CSE student."""
        self.client.force_login(self.asst_cse)
        response = self.client.post(
            reverse('applications:update_stage', kwargs={'application_id': self.app_a.id}),
            {'stage': ApplicationStage.TECHNICAL_ROUND, 'remarks': 'Cleared test'}
        )
        self.assertEqual(response.status_code, 302)
        self.app_a.refresh_from_db()
        self.assertEqual(self.app_a.stage, ApplicationStage.TECHNICAL_ROUND)

    def test_student_drive_detail_hides_candidate_roster(self):
        """When a student views a placement drive, the candidate roster is hidden and empty."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('placements:drive_detail', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['applications']), 0)
        # Should not display other students' emails in the HTML
        self.assertNotContains(response, 'student.b@apex.edu.in')
        self.assertNotContains(response, '21ECE001')

    def test_assistant_drive_detail_scopes_roster_to_assigned_dept(self):
        """CSE Assistant sees only CSE applicants on the drive detail page."""
        self.client.force_login(self.asst_cse)
        response = self.client.get(reverse('placements:drive_detail', kwargs={'job_id': self.job.id}))
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].student.department.code, 'CSE')
        self.assertContains(response, '21CSE001')
        self.assertNotContains(response, '21ECE001')

    def test_change_password_workflow(self):
        """User can change password with correct current password; rejected with wrong current password."""
        self.client.force_login(self.user_a)

        # Wrong current password
        resp_fail = self.client.post(reverse('accounts:change_password'), {
            'current_password': 'WrongPassword',
            'new_password': 'BrandNewPassword@123',
            'confirm_password': 'BrandNewPassword@123'
        })
        self.assertEqual(resp_fail.status_code, 200)
        self.assertContains(resp_fail, 'Current password is incorrect.')

        # Valid password change
        resp_success = self.client.post(reverse('accounts:change_password'), {
            'current_password': 'Password@123',
            'new_password': 'BrandNewPassword@123',
            'confirm_password': 'BrandNewPassword@123'
        })
        self.assertEqual(resp_success.status_code, 302)

        # Verify new password works
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password('BrandNewPassword@123'))

    def test_role_broadcast_notification_visibility(self):
        """Broadcast notification targeting STUDENT is visible in notification list and context processor."""
        Notification.objects.create(
            target_role='STUDENT',
            title='Campus Recruitment Alert',
            message='New drive scheduled for tomorrow',
            action_url='/student/jobs/'
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('accounts:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Campus Recruitment Alert')
        # Context processor should reflect at least 1 unread notification
        self.assertGreaterEqual(response.context['UNREAD_NOTIFICATIONS_COUNT'], 1)
