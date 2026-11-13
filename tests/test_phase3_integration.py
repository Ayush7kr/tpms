from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile, PlacementStatus
from apps.companies.models import Company, CompanyTier
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication, ApplicationStage, VerificationStatus
from apps.notifications.models import Notification
from apps.audit.models import AuditLog


class Phase3IntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Departments
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science & Engineering')
        self.dept_ece = Department.objects.create(code='ECE', name='Electronics & Communication')
        self.dept_empty = Department.objects.create(code='CIVIL', name='Civil Engineering')

        # Users
        self.admin = User.objects.create_superuser(
            'admin@apex.edu.in', 'Admin@123', first_name='Admin', last_name='User', role=UserRole.ADMIN
        )
        self.admin2 = User.objects.create_user(
            'admin2@apex.edu.in', 'Admin@123', first_name='AdminTwo', last_name='User', role=UserRole.ADMIN
        )
        self.principal = User.objects.create_user(
            'principal@apex.edu.in', 'Password@123', first_name='Dr. Rajesh', last_name='Sharma', role=UserRole.PRINCIPAL
        )
        self.tpo = User.objects.create_user(
            'tpo@apex.edu.in', 'Password@123', first_name='Prof. Vikram', last_name='Malhotra', role=UserRole.TNP_OFFICER
        )

        self.student_user = User.objects.create_user(
            'student@apex.edu.in', 'Password@123', first_name='Aarav', last_name='Mehta', role=UserRole.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            department=self.dept_cse,
            roll_number='21CSE001',
            prn_number='PRN21001',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('91.50'),
            twelfth_percentage=Decimal('89.20'),
            graduation_cgpa=Decimal('8.82'),
            active_backlogs=0,
            skills='Python, Django',
            placement_status=PlacementStatus.UNPLACED
        )

        # Company & Drive
        self.company = Company.objects.create(
            name='Acme Corp',
            tier=CompanyTier.TIER_1_DREAM,
            website='https://acme.example.com',
            contact_person='Jane Doe',
            contact_email='jane@acme.example.com',
            industry_sector='Information Technology',
            is_active=True
        )

        self.job = JobOpening.objects.create(
            company=self.company,
            title='Software Engineer',
            role_description='Backend Python/Django Developer',
            job_location='Bangalore',
            package_ctc=Decimal('12.50'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            allowed_batches='2025',
            allowed_degrees='B.Tech',
            application_deadline=timezone.now() + timedelta(days=7),
            drive_date=(timezone.now() + timedelta(days=14)).date(),
            status=JobStatus.PUBLISHED,
            created_by=self.tpo
        )
        self.job.allowed_departments.add(self.dept_cse)
        DepartmentJobApproval.objects.create(
            job_opening=self.job,
            department=self.dept_cse,
            status=ApprovalStatus.APPROVED
        )

    def test_student_can_withdraw_applied_application(self):
        """A student should be able to withdraw an application before selection rounds commence."""
        app = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student,
            stage=ApplicationStage.APPLIED
        )

        self.client.login(username='student@apex.edu.in', password='Password@123')
        response = self.client.post(reverse('applications:withdraw', args=[app.id]))

        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.stage, ApplicationStage.WITHDRAWN)

        # Verify audit log was recorded
        audit = AuditLog.objects.filter(action='APPLICATION_WITHDRAWN', entity_id=str(app.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.student_user)

    def test_student_cannot_withdraw_progressed_application(self):
        """A student cannot withdraw once shortlisted or undergoing interview rounds."""
        app = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student,
            stage=ApplicationStage.SHORTLISTED
        )

        self.client.login(username='student@apex.edu.in', password='Password@123')
        response = self.client.post(reverse('applications:withdraw', args=[app.id]))

        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.stage, ApplicationStage.SHORTLISTED)

    def test_cannot_advance_withdrawn_or_cancelled_application(self):
        """TPO cannot advance an application that has been withdrawn or is part of a cancelled drive."""
        app = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student,
            stage=ApplicationStage.WITHDRAWN
        )

        self.client.login(username='tpo@apex.edu.in', password='Password@123')
        response = self.client.post(
            reverse('applications:update_stage', args=[app.id]),
            {'stage': ApplicationStage.TECHNICAL_ROUND}
        )

        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.stage, ApplicationStage.WITHDRAWN)

    def test_offer_reversal_syncs_placement_status_back_to_unplaced(self):
        """Revoking or moving an offered student to rejected reverts placement status to unplaced."""
        app = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student,
            stage=ApplicationStage.TECHNICAL_ROUND
        )

        self.client.login(username='tpo@apex.edu.in', password='Password@123')

        # Advance to OFFERED
        self.client.post(
            reverse('applications:update_stage', args=[app.id]),
            {'stage': ApplicationStage.OFFERED}
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.placement_status, PlacementStatus.PLACED)
        self.assertEqual(self.student.placed_company, self.company)
        self.assertEqual(self.student.salary_package, self.job.package_ctc)

        # Revert to REJECTED (e.g. background check failure or declined offer)
        self.client.post(
            reverse('applications:update_stage', args=[app.id]),
            {'stage': ApplicationStage.REJECTED}
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.placement_status, PlacementStatus.UNPLACED)
        self.assertIsNone(self.student.placed_company)
        self.assertIsNone(self.student.salary_package)

    def test_deactivated_user_session_evicted(self):
        """When an account is deactivated, existing active sessions are evicted immediately."""
        self.client.login(username='student@apex.edu.in', password='Password@123')
        res = self.client.get(reverse('student_panel:dashboard'))
        self.assertEqual(res.status_code, 200)

        # Admin deactivates student
        self.student_user.is_active = False
        self.student_user.save()

        # Subsequent request must be rejected and logged out
        res2 = self.client.get(reverse('student_panel:dashboard'))
        self.assertEqual(res2.status_code, 302)
        self.assertIn(reverse('accounts:login'), res2.url)

    def test_admin_cannot_delete_self(self):
        """Admin cannot delete their own account."""
        self.client.login(username='admin@apex.edu.in', password='Admin@123')
        res = self.client.post(reverse('admin_panel:user_delete', args=[self.admin.id]))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_admin_cannot_delete_last_admin(self):
        """Cannot delete an administrator account if only one active administrator remains."""
        # Deactivate admin2 so self.admin is the only active admin
        self.admin2.is_active = False
        self.admin2.save()
        self.assertEqual(User.objects.filter(role=UserRole.ADMIN, is_active=True).count(), 1)

        self.client.login(username='admin@apex.edu.in', password='Admin@123')
        res = self.client.post(reverse('admin_panel:user_delete', args=[self.admin2.id]))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(id=self.admin2.id).exists())

    def test_admin_cannot_delete_department_with_students(self):
        """A department containing enrolled student records cannot be deleted."""
        self.client.login(username='admin@apex.edu.in', password='Admin@123')
        res = self.client.post(reverse('admin_panel:department_delete', args=[self.dept_cse.id]))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Department.objects.filter(id=self.dept_cse.id).exists())

    def test_admin_can_delete_empty_department(self):
        """An empty department with no students or drives can be cleanly deleted."""
        self.client.login(username='admin@apex.edu.in', password='Admin@123')
        res = self.client.post(reverse('admin_panel:department_delete', args=[self.dept_empty.id]))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Department.objects.filter(id=self.dept_empty.id).exists())

    def test_company_detail_view_renders_drives_and_placements(self):
        """Company detail page displays corporate metrics, active drives, and placed students."""
        # Mark student as placed at company
        self.student.placement_status = PlacementStatus.PLACED
        self.student.placed_company = self.company
        self.student.salary_package = Decimal('12.50')
        self.student.save()

        self.client.login(username='tpo@apex.edu.in', password='Password@123')
        res = self.client.get(reverse('companies:detail', args=[self.company.id]))

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Acme Corp')
        self.assertContains(res, 'Software Engineer')
        self.assertContains(res, '21CSE001')
        self.assertContains(res, 'Aarav Mehta')

    def test_drive_cancellation_notifies_applicants(self):
        """Marking a recruitment drive CANCELLED automatically notifies all applicants."""
        app = JobApplication.objects.create(
            job_opening=self.job,
            student=self.student,
            stage=ApplicationStage.APPLIED
        )

        self.client.login(username='tpo@apex.edu.in', password='Password@123')
        post_data = {
            'company': self.company.id,
            'title': self.job.title,
            'role_description': self.job.role_description,
            'job_location': self.job.job_location,
            'package_ctc': str(self.job.package_ctc),
            'min_tenth_percentage': '0',
            'min_twelfth_percentage': '0',
            'min_graduation_cgpa': '7.0',
            'max_active_backlogs': '0',
            'allowed_departments': [self.dept_cse.id],
            'allowed_batches': '2025',
            'allowed_degrees': 'B.Tech',
            'application_deadline': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
            'drive_date': (timezone.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'status': JobStatus.CANCELLED
        }

        res = self.client.post(reverse('placements:job_edit', args=[self.job.id]), post_data)
        self.assertEqual(res.status_code, 302)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.CANCELLED)

        notif = Notification.objects.filter(recipient=self.student_user).first()
        self.assertIsNotNone(notif)
        self.assertIn('Cancelled', notif.title)
