from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.departments.models import Department
from apps.companies.models import Company
from apps.students.models import StudentProfile, PlacementStatus
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.placements.services.eligibility import EligibilityEngine


class EligibilityEngineTests(TestCase):
    def setUp(self):
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science')
        self.dept_mech = Department.objects.create(code='MECH', name='Mechanical')

        self.company = Company.objects.create(
            name='Test Tech',
            industry_sector='IT',
            contact_person='HR',
            contact_email='hr@testtech.com'
        )

        now = timezone.now()
        self.job = JobOpening.objects.create(
            company=self.company,
            title='Software Engineer',
            role_description='Coding',
            job_location='Bangalore',
            package_ctc=Decimal('12.00'),
            min_tenth_percentage=Decimal('75.00'),
            min_twelfth_percentage=Decimal('75.00'),
            min_graduation_cgpa=Decimal('8.00'),
            max_active_backlogs=0,
            allowed_batches='2025',
            application_deadline=now + datetime.timedelta(days=7),
            drive_date=now.date() + datetime.timedelta(days=14),
            status=JobStatus.PUBLISHED
        )
        self.job.allowed_departments.add(self.dept_cse)

        # Department Approval for CSE
        self.approval = DepartmentJobApproval.objects.create(
            job_opening=self.job,
            department=self.dept_cse,
            status=ApprovalStatus.APPROVED
        )

        # Student with high scores
        user1 = User.objects.create_user(email='eligible@apex.edu.in', password='pwd', first_name='A', last_name='B', role=UserRole.STUDENT)
        self.student_eligible = StudentProfile.objects.create(
            user=user1,
            department=self.dept_cse,
            roll_number='21CSE001',
            prn_number='PRN001',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('85.00'),
            twelfth_percentage=Decimal('82.00'),
            graduation_cgpa=Decimal('8.50'),
            active_backlogs=0
        )

    def test_eligible_student_evaluation(self):
        """Student meeting all criteria is evaluated as eligible."""
        result = EligibilityEngine.evaluate(self.student_eligible, self.job)
        self.assertTrue(result['is_eligible'])
        self.assertTrue(result['can_apply'])
        self.assertEqual(len(result['failed_criteria']), 0)

    def test_cgpa_below_cutoff_fails(self):
        """Student with CGPA below cut-off is evaluated as ineligible."""
        self.student_eligible.graduation_cgpa = Decimal('7.80')
        self.student_eligible.save()

        result = EligibilityEngine.evaluate(self.student_eligible, self.job)
        self.assertFalse(result['is_eligible'])
        self.assertFalse(result['can_apply'])
        self.assertTrue(any('CGPA' in reason for reason in result['failed_criteria']))

    def test_active_backlogs_exceeding_fails(self):
        """Student with backlogs exceeding max is ineligible."""
        self.student_eligible.active_backlogs = 1
        self.student_eligible.save()

        result = EligibilityEngine.evaluate(self.student_eligible, self.job)
        self.assertFalse(result['is_eligible'])
        self.assertTrue(any('Backlogs' in reason for reason in result['failed_criteria']))

    def test_ineligible_department_fails(self):
        """Student from an unlisted department is ineligible."""
        self.student_eligible.department = self.dept_mech
        self.student_eligible.save()

        result = EligibilityEngine.evaluate(self.student_eligible, self.job)
        self.assertFalse(result['is_eligible'])
        self.assertTrue(any('Department' in reason for reason in result['failed_criteria']))

    def test_unapproved_department_drive_blocks_application(self):
        """Drive unapproved by assistant is blocked."""
        self.approval.status = ApprovalStatus.PENDING
        self.approval.save()

        result = EligibilityEngine.evaluate(self.student_eligible, self.job)
        self.assertFalse(result['is_eligible'])
        self.assertTrue(any('pending activation' in reason for reason in result['failed_criteria']))
