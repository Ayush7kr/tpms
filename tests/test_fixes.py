"""Regression tests for bugs fixed during the UI/quality pass."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.applications.models import JobApplication, ApplicationStage
from apps.companies.models import Company
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.notifications.models import Notification
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.placements.services.eligibility import EligibilityEngine
from apps.students.models import StudentProfile, PlacementStatus
from apps.study_materials.models import StudyMaterial, ResourceType


class Base(TestCase):
    def setUp(self):
        self.cse = Department.objects.create(code='CSE', name='Computer Science')
        self.company = Company.objects.create(name='Acme', industry_sector='IT', contact_person='HR', contact_email='hr@acme.test')
        self.company2 = Company.objects.create(name='Beta', industry_sector='IT', contact_person='HR', contact_email='hr@beta.test')
        self.admin = User.objects.create_user(email='admin@t.in', password='pass12345', first_name='Ad', last_name='Min', role=UserRole.ADMIN)
        self.tpo = User.objects.create_user(email='tpo@t.in', password='pass12345', first_name='T', last_name='PO', role=UserRole.TNP_OFFICER)
        su = User.objects.create_user(email='stu@t.in', password='pass12345', first_name='S', last_name='Tu', role=UserRole.STUDENT)
        self.student = StudentProfile.objects.create(
            user=su, department=self.cse, roll_number='R1', prn_number='P1', batch_year=2025, degree='B.Tech',
            tenth_percentage=Decimal('90'), twelfth_percentage=Decimal('90'), graduation_cgpa=Decimal('9'), active_backlogs=0)
        self.job = self.make_job(self.company, Decimal('10'))
        self.job2 = self.make_job(self.company2, Decimal('20'))

    def make_job(self, company, pkg, degrees='B.Tech'):
        job = JobOpening.objects.create(
            company=company, title='SDE', role_description='x', job_location='Pune', package_ctc=pkg,
            allowed_batches='2025', allowed_degrees=degrees,
            application_deadline=timezone.now() + timedelta(days=5),
            drive_date=(timezone.now() + timedelta(days=10)).date(), status=JobStatus.PUBLISHED)
        job.allowed_departments.add(self.cse)
        DepartmentJobApproval.objects.create(job_opening=job, department=self.cse, status=ApprovalStatus.APPROVED)
        return job


class EligibilityFixes(Base):
    def test_degree_is_enforced(self):
        job = self.make_job(self.company, Decimal('5'), degrees='MCA')
        self.assertFalse(EligibilityEngine.evaluate(self.student, job)['is_eligible'])

    def test_can_reapply_after_withdrawing(self):
        c = Client(); c.force_login(self.student.user)
        c.post(reverse('applications:apply', args=[self.job.id]))
        app = JobApplication.objects.get(student=self.student, job_opening=self.job)
        c.post(reverse('applications:withdraw', args=[app.id]))
        self.assertTrue(EligibilityEngine.evaluate(self.student, self.job)['can_apply'])
        c.post(reverse('applications:apply', args=[self.job.id]))
        app.refresh_from_db()
        self.assertEqual(app.stage, ApplicationStage.APPLIED)


class OfferFixes(Base):
    def test_revoking_one_offer_keeps_other_offer(self):
        a1 = JobApplication.objects.create(job_opening=self.job, student=self.student)
        a2 = JobApplication.objects.create(job_opening=self.job2, student=self.student)
        c = Client(); c.force_login(self.tpo)
        c.post(reverse('applications:update_stage', args=[a1.id]), {'stage': 'OFFERED'})
        c.post(reverse('applications:update_stage', args=[a2.id]), {'stage': 'OFFERED'})
        c.post(reverse('applications:update_stage', args=[a2.id]), {'stage': 'REJECTED'})
        self.student.refresh_from_db()
        self.assertEqual(self.student.placement_status, PlacementStatus.PLACED)
        self.assertEqual(self.student.placed_company, self.company)

    def test_lower_offer_does_not_replace_higher(self):
        a1 = JobApplication.objects.create(job_opening=self.job2, student=self.student)
        a2 = JobApplication.objects.create(job_opening=self.job, student=self.student)
        c = Client(); c.force_login(self.tpo)
        c.post(reverse('applications:update_stage', args=[a1.id]), {'stage': 'OFFERED'})
        c.post(reverse('applications:update_stage', args=[a2.id]), {'stage': 'OFFERED'})
        self.student.refresh_from_db()
        self.assertEqual(self.student.salary_package, Decimal('20'))


class NotificationFixes(Base):
    def test_mark_all_read_clears_role_broadcasts(self):
        Notification.objects.create(target_role='STUDENT', title='New drive', message='x')
        c = Client(); c.force_login(self.student.user)
        r = c.get(reverse('student_panel:dashboard'))
        self.assertEqual(r.context['UNREAD_NOTIFICATIONS_COUNT'], 1)
        c.post(reverse('accounts:notifications'), {'action': 'mark_all_read'})
        r = c.get(reverse('student_panel:dashboard'))
        self.assertEqual(r.context['UNREAD_NOTIFICATIONS_COUNT'], 0)


class SecurityFixes(Base):
    @override_settings(DEMO_MODE=False)
    def test_role_switch_disabled_outside_demo_mode(self):
        r = Client().post(reverse('accounts:quick_switch', args=['ADMIN']))
        self.assertEqual(r.status_code, 404)

    @override_settings(DEMO_MODE=True)
    def test_role_switch_requires_post(self):
        c = Client()
        c.get(reverse('accounts:quick_switch', args=['ADMIN']))
        self.assertNotIn('_auth_user_id', c.session)

    def test_students_cannot_open_institution_analytics(self):
        c = Client(); c.force_login(self.student.user)
        r = c.get(reverse('analytics:salary_stats'))
        self.assertEqual(r.status_code, 302)

    def test_toggle_user_requires_post(self):
        c = Client(); c.force_login(self.admin)
        c.get(reverse('admin_panel:user_toggle', args=[self.tpo.id]))
        self.tpo.refresh_from_db()
        self.assertTrue(self.tpo.is_active)

    def test_admin_cannot_demote_self(self):
        c = Client(); c.force_login(self.admin)
        c.post(reverse('admin_panel:user_edit', args=[self.admin.id]), {
            'first_name': 'Ad', 'last_name': 'Min', 'email': 'admin@t.in', 'role': 'STUDENT', 'is_active': 'on'})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, UserRole.ADMIN)

    def test_student_without_profile_gets_page_not_crash(self):
        u = User.objects.create_user(email='new@t.in', password='pass12345', first_name='N', last_name='U', role=UserRole.STUDENT)
        c = Client(); c.force_login(u)
        for name in ('student_panel:dashboard', 'student_panel:eligible_jobs', 'student_panel:profile'):
            self.assertEqual(c.get(reverse(name)).status_code, 200)


class MaterialFixes(Base):
    def test_students_see_college_wide_materials(self):
        StudyMaterial.objects.create(title='Aptitude pack', category='APTITUDE', resource_type=ResourceType.EXTERNAL_URL,
                                     external_url='https://example.com')
        c = Client(); c.force_login(self.student.user)
        r = c.get(reverse('study_materials:list'))
        self.assertContains(r, 'Aptitude pack')


class DriveValidationFixes(Base):
    def test_deadline_in_past_rejected(self):
        c = Client(); c.force_login(self.tpo)
        r = c.post(reverse('placements:post_job'), {
            'company_id': self.company.id, 'title': 'Past', 'role_description': 'x', 'job_location': 'Pune',
            'package_ctc': '5', 'allowed_departments': [self.cse.id],
            'application_deadline': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'drive_date': timezone.now().strftime('%Y-%m-%d')})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(JobOpening.objects.filter(title='Past').exists())

    def test_cgpa_cutoff_above_10_rejected(self):
        c = Client(); c.force_login(self.tpo)
        c.post(reverse('placements:post_job'), {
            'company_id': self.company.id, 'title': 'Bad', 'role_description': 'x', 'job_location': 'Pune',
            'package_ctc': '5', 'allowed_departments': [self.cse.id], 'min_graduation_cgpa': '85',
            'application_deadline': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'drive_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d')})
        self.assertFalse(JobOpening.objects.filter(title='Bad').exists())


class CoordinatorPostingScope(Base):
    def test_coordinator_post_is_limited_to_own_branches(self):
        ece = Department.objects.create(code='ECE', name='Electronics')
        coord = User.objects.create_user(email='coord@t.in', password='pass12345', first_name='C', last_name='O', role=UserRole.TNP_ASSISTANT)
        AssistantDepartmentAssignment.objects.create(assistant=coord, department=self.cse)
        c = Client(); c.force_login(coord)
        c.post(reverse('placements:post_job'), {
            'company_id': self.company.id, 'title': 'Cross', 'role_description': 'x', 'job_location': 'Pune',
            'package_ctc': '5', 'allowed_departments': [self.cse.id, ece.id],
            'application_deadline': (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
            'drive_date': (timezone.now() + timedelta(days=5)).strftime('%Y-%m-%d')})
        job = JobOpening.objects.get(title='Cross')
        self.assertEqual(list(job.allowed_departments.values_list('code', flat=True)), ['CSE'])
        self.assertEqual(job.department_approvals.get(department=self.cse).status, ApprovalStatus.APPROVED)
        self.assertFalse(job.department_approvals.filter(department=ece).exists())
