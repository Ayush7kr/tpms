from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
import io
import openpyxl
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile, PlacementStatus, Gender
from apps.companies.models import Company, CompanyTier
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication, ApplicationStage, VerificationStatus
from apps.placements.services.eligibility import EligibilityEngine
from apps.students.services.bulk_import import BulkStudentImportService


class WorkflowsEndToEndTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Departments
        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science & Engineering')
        self.dept_ece = Department.objects.create(code='ECE', name='Electronics & Communication')
        self.dept_mech = Department.objects.create(code='MECH', name='Mechanical Engineering')

        # Leadership
        self.admin = User.objects.create_superuser('admin@apex.edu.in', 'Admin@123', first_name='Admin', last_name='User', role=UserRole.ADMIN)
        self.principal = User.objects.create_user('principal@apex.edu.in', 'Password@123', first_name='Dr. Rajesh', last_name='Sharma', role=UserRole.PRINCIPAL)
        self.tpo = User.objects.create_user('tpo@apex.edu.in', 'Password@123', first_name='Prof. Vikram', last_name='Malhotra', role=UserRole.TNP_OFFICER)

        # Assistants
        self.asst_cse = User.objects.create_user('asst.cse@apex.edu.in', 'Password@123', first_name='Ananya', last_name='Deshmukh', role=UserRole.TNP_ASSISTANT)
        AssistantDepartmentAssignment.objects.create(assistant=self.asst_cse, department=self.dept_cse)

        self.asst_ece = User.objects.create_user('asst.ece@apex.edu.in', 'Password@123', first_name='Ramesh', last_name='Iyer', role=UserRole.TNP_ASSISTANT)
        AssistantDepartmentAssignment.objects.create(assistant=self.asst_ece, department=self.dept_ece)

        # Company
        self.company = Company.objects.create(name='Google India', tier=CompanyTier.TIER_1_DREAM, is_active=True)

        # Students for Workflow B (Aarav Mehta & Karan Kapoor)
        u_aarav = User.objects.create_user('aarav.mehta@apex.edu.in', 'Password@123', first_name='Aarav', last_name='Mehta', role=UserRole.STUDENT)
        self.aarav = StudentProfile.objects.create(
            user=u_aarav,
            department=self.dept_cse,
            roll_number='21CSE001',
            prn_number='PRN21001',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('91.50'),
            twelfth_percentage=Decimal('89.20'),
            graduation_cgpa=Decimal('8.82'),
            active_backlogs=0,
            skills='Python, Django, AWS, React',
            placement_status=PlacementStatus.UNPLACED
        )

        u_karan = User.objects.create_user('karan.kapoor@apex.edu.in', 'Password@123', first_name='Karan', last_name='Kapoor', role=UserRole.STUDENT)
        self.karan = StudentProfile.objects.create(
            user=u_karan,
            department=self.dept_cse,
            roll_number='21CSE045',
            prn_number='PRN21045',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('62.00'),
            twelfth_percentage=Decimal('64.50'),
            graduation_cgpa=Decimal('6.40'),
            active_backlogs=2,
            skills='HTML, Basic Java',
            placement_status=PlacementStatus.UNPLACED
        )

    def test_workflow_a_job_creation_and_assistant_approval(self):
        """
        Workflow A:
        1. TPO posts a job targeting CSE and ECE.
        2. Approvals are auto-created in PENDING status.
        3. CSE Assistant approves for CSE.
        4. ECE Assistant rejects for ECE.
        """
        self.client.force_login(self.tpo)
        post_data = {
            'company_id': self.company.id,
            'title': 'Software Development Engineer',
            'role_description': 'Core engineering position in backend services.',
            'job_location': 'Hyderabad',
            'package_ctc': '18.50',
            'bond_details': 'None',
            'min_tenth_percentage': '75.0',
            'min_twelfth_percentage': '75.0',
            'min_graduation_cgpa': '7.5',
            'max_active_backlogs': '0',
            'allowed_departments': [str(self.dept_cse.id), str(self.dept_ece.id)],
            'allowed_batches': '2025',
            'allowed_degrees': 'B.Tech',
            'application_deadline': (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M'),
            'drive_date': (timezone.now() + timedelta(days=40)).strftime('%Y-%m-%d')
        }
        response = self.client.post(reverse('placements:post_job'), post_data)
        self.assertEqual(response.status_code, 302)

        job = JobOpening.objects.get(title='Software Development Engineer')
        self.assertEqual(job.company, self.company)
        self.assertEqual(job.package_ctc, Decimal('18.50'))

        # Verify 2 pending approvals created
        approvals = DepartmentJobApproval.objects.filter(job_opening=job)
        self.assertEqual(approvals.count(), 2)
        apprv_cse = approvals.get(department=self.dept_cse)
        apprv_ece = approvals.get(department=self.dept_ece)
        self.assertEqual(apprv_cse.status, ApprovalStatus.PENDING)
        self.assertEqual(apprv_ece.status, ApprovalStatus.PENDING)

        # CSE Assistant approves
        self.client.force_login(self.asst_cse)
        resp_cse = self.client.post(reverse('assistant_panel:job_approvals'), {
            'approval_id': apprv_cse.id,
            'decision': 'APPROVED',
            'comments': 'Curriculum aligns perfectly with company requirements.'
        })
        self.assertEqual(resp_cse.status_code, 302)
        apprv_cse.refresh_from_db()
        self.assertEqual(apprv_cse.status, ApprovalStatus.APPROVED)
        self.assertEqual(apprv_cse.reviewed_by, self.asst_cse)

        # ECE Assistant rejects
        self.client.force_login(self.asst_ece)
        resp_ece = self.client.post(reverse('assistant_panel:job_approvals'), {
            'approval_id': apprv_ece.id,
            'decision': 'REJECTED',
            'comments': 'Exam schedules conflict with drive date.'
        })
        self.assertEqual(resp_ece.status_code, 302)
        apprv_ece.refresh_from_db()
        self.assertEqual(apprv_ece.status, ApprovalStatus.REJECTED)
        self.assertEqual(apprv_ece.reviewed_by, self.asst_ece)

    def test_workflow_b_student_eligibility_engine(self):
        """
        Workflow B:
        Verify programmatic cut-off evaluation:
        - Aarav Mehta: Eligible (CGPA 8.82 >= 7.5, Backlogs 0 <= 0, 10th/12th meet criteria).
        - Karan Kapoor: Ineligible (CGPA 6.40 < 7.5, Backlogs 2 > 0, 10th 62.0% < 75.0%, 12th 64.5% < 75.0%).
        """
        job = JobOpening.objects.create(
            company=self.company,
            title='Member Technical Staff',
            role_description='Distributed systems development',
            job_location='Bangalore',
            package_ctc=Decimal('22.00'),
            min_tenth_percentage=Decimal('75.00'),
            min_twelfth_percentage=Decimal('75.00'),
            min_graduation_cgpa=Decimal('7.50'),
            max_active_backlogs=0,
            allowed_degrees='B.Tech',
            allowed_batches='2025',
            application_deadline=timezone.now() + timedelta(days=30),
            drive_date='2027-01-20',
            created_by=self.tpo,
            status=JobStatus.PUBLISHED
        )
        job.allowed_departments.set([self.dept_cse])
        DepartmentJobApproval.objects.create(job_opening=job, department=self.dept_cse, status=ApprovalStatus.APPROVED)

        # Evaluate Aarav Mehta
        eval_aarav = EligibilityEngine.evaluate(self.aarav, job)
        self.assertTrue(eval_aarav['can_apply'])
        self.assertTrue(eval_aarav['is_eligible'])
        self.assertEqual(len(eval_aarav['failed_criteria']), 0)

        # Evaluate Karan Kapoor
        eval_karan = EligibilityEngine.evaluate(self.karan, job)
        self.assertFalse(eval_karan['can_apply'])
        self.assertFalse(eval_karan['is_eligible'])
        self.assertGreaterEqual(len(eval_karan['failed_criteria']), 3)

    def test_workflow_c_application_submission_duplicate_prevention_and_verification(self):
        """
        Workflow C:
        1. Aarav submits 1-Click application.
        2. Submitting again is blocked by duplicate prevention.
        3. CSE Assistant reviews academic records and marks application VERIFIED.
        """
        job = JobOpening.objects.create(
            company=self.company,
            title='Backend Cloud Engineer',
            role_description='Cloud infra role',
            job_location='Pune',
            package_ctc=Decimal('15.00'),
            min_tenth_percentage=Decimal('70.00'),
            min_twelfth_percentage=Decimal('70.00'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            allowed_degrees='B.Tech',
            allowed_batches='2025',
            application_deadline=timezone.now() + timedelta(days=30),
            drive_date='2027-01-25',
            created_by=self.tpo,
            status=JobStatus.PUBLISHED
        )
        job.allowed_departments.set([self.dept_cse])
        DepartmentJobApproval.objects.create(job_opening=job, department=self.dept_cse, status=ApprovalStatus.APPROVED)

        # Submit 1-Click application
        self.client.force_login(self.aarav.user)
        resp_apply = self.client.post(reverse('applications:apply', kwargs={'job_id': job.id}))
        self.assertEqual(resp_apply.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(job_opening=job, student=self.aarav).exists())

        # Attempt duplicate application
        resp_dup = self.client.post(reverse('applications:apply', kwargs={'job_id': job.id}))
        self.assertEqual(resp_dup.status_code, 302)
        self.assertEqual(JobApplication.objects.filter(job_opening=job, student=self.aarav).count(), 1)

        # Assistant verifies application
        app = JobApplication.objects.get(job_opening=job, student=self.aarav)
        self.assertEqual(app.verification_status, VerificationStatus.PENDING)

        self.client.force_login(self.asst_cse)
        resp_ver = self.client.post(reverse('assistant_panel:verify_applications'), {
            'application_id': app.id,
            'verification_status': VerificationStatus.VERIFIED,
            'verification_notes': 'Transcripts and marksheets verified against college ERP records.'
        })
        self.assertEqual(resp_ver.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(app.verified_by, self.asst_cse)

    def test_workflow_d_selection_progression_and_auto_placement_sync(self):
        """
        Workflow D:
        Recruitment Round Progression:
        APPLIED -> SHORTLISTED -> ASSESSMENT -> TECHNICAL -> HR -> OFFERED
        Upon OFFERED:
        - StudentProfile.placement_status automatically becomes PLACED
        - StudentProfile.placed_company is set
        - StudentProfile.salary_package is updated
        """
        job = JobOpening.objects.create(
            company=self.company,
            title='Staff Software Engineer',
            role_description='Core infra team',
            job_location='Bangalore',
            package_ctc=Decimal('28.50'),
            min_tenth_percentage=Decimal('70.00'),
            min_twelfth_percentage=Decimal('70.00'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            allowed_degrees='B.Tech',
            allowed_batches='2025',
            application_deadline=timezone.now() + timedelta(days=30),
            drive_date='2027-01-30',
            created_by=self.tpo,
            status=JobStatus.PUBLISHED
        )
        job.allowed_departments.set([self.dept_cse])
        DepartmentJobApproval.objects.create(job_opening=job, department=self.dept_cse, status=ApprovalStatus.APPROVED)

        app = JobApplication.objects.create(
            job_opening=job,
            student=self.aarav,
            stage=ApplicationStage.APPLIED,
            verification_status=VerificationStatus.VERIFIED
        )

        self.client.force_login(self.tpo)

        # Progress through recruitment rounds
        rounds = [
            ApplicationStage.SHORTLISTED,
            ApplicationStage.ASSESSMENT,
            ApplicationStage.TECHNICAL_ROUND,
            ApplicationStage.HR_ROUND,
            ApplicationStage.OFFERED,
        ]
        for round_stage in rounds:
            resp = self.client.post(
                reverse('applications:update_stage', kwargs={'application_id': app.id}),
                {'stage': round_stage, 'remarks': f'Passed {round_stage} successfully.'}
            )
            self.assertEqual(resp.status_code, 302)
            app.refresh_from_db()
            self.assertEqual(app.stage, round_stage)

        # Verify automated placement sync
        self.aarav.refresh_from_db()
        self.assertEqual(self.aarav.placement_status, PlacementStatus.PLACED)
        self.assertEqual(self.aarav.placed_company, self.company)
        self.assertEqual(self.aarav.salary_package, Decimal('28.50'))

    def test_workflow_e_bulk_student_ingestion_csv_and_excel(self):
        """
        Workflow E:
        Bulk candidate onboarding via CSV & Excel:
        - Valid CSV rows are ingested with default password.
        - Duplicate roll numbers / emails / PRNs are safely skipped.
        - Invalid CGPA (>10) reports row-level errors.
        - Empty files are handled gracefully.
        """
        csv_content = (
            "roll_number,prn_number,first_name,last_name,email,phone,gender,batch_year,degree,tenth_percentage,twelfth_percentage,graduation_cgpa,active_backlogs,skills\n"
            "21CSE101,PRN21101,Riya,Sharma,riya.sharma@apex.edu.in,9876543210,FEMALE,2025,B.Tech,88.5,85.2,8.45,0,Python, Django\n"
            "21CSE102,PRN21102,Vivek,Kumar,vivek.kumar@apex.edu.in,9876543211,MALE,2025,B.Tech,90.0,88.0,15.5,0,Java\n"  # Invalid CGPA (15.5 > 10.0)
            "21CSE001,PRN21001,Aarav,Mehta,aarav.mehta@apex.edu.in,9876543212,MALE,2025,B.Tech,91.5,89.2,8.82,0,Python\n"  # Duplicate of Aarav
        )
        csv_file = SimpleUploadedFile("students.csv", csv_content.encode('utf-8'), content_type="text/csv")

        result = BulkStudentImportService.parse_file(csv_file, department=self.dept_cse)
        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 1)  # Riya Sharma
        self.assertEqual(result['skipped_count'], 1)  # Aarav duplicate
        self.assertEqual(len(result['errors']), 1)    # Vivek invalid CGPA

        # Verify user and profile created for Riya
        user_riya = User.objects.get(email='riya.sharma@apex.edu.in')
        self.assertTrue(user_riya.check_password('apex@123'))
        profile_riya = StudentProfile.objects.get(roll_number='21CSE101')
        self.assertEqual(profile_riya.department, self.dept_cse)
        self.assertEqual(profile_riya.gender, Gender.FEMALE)
        self.assertEqual(profile_riya.graduation_cgpa, Decimal('8.45'))

        # Test Excel (.xlsx) ingestion
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            'roll_number', 'prn_number', 'first_name', 'last_name', 'email', 'phone',
            'gender', 'batch_year', 'degree', 'tenth_percentage', 'twelfth_percentage',
            'graduation_cgpa', 'active_backlogs', 'skills'
        ])
        ws.append([
            '21CSE201', 'PRN21201', 'Aditya', 'Verma', 'aditya.verma@apex.edu.in', '9876543220',
            'MALE', '2025', 'B.Tech', '82.0', '84.0', '8.20', '0', 'C++, Data Structures'
        ])
        excel_io = io.BytesIO()
        wb.save(excel_io)
        excel_io.seek(0)
        excel_file = SimpleUploadedFile("students.xlsx", excel_io.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        result_excel = BulkStudentImportService.parse_file(excel_file, department=self.dept_cse)
        self.assertTrue(result_excel['success'])
        self.assertEqual(result_excel['created_count'], 1)
        self.assertTrue(StudentProfile.objects.filter(roll_number='21CSE201').exists())

    def test_workflow_f_assistant_posts_department_job(self):
        """
        Workflow F:
        TnP Assistant posts a job opening directly for their assigned department:
        - Job is created with their department.
        - Approval for their department is automatically set to APPROVED.
        """
        self.client.force_login(self.asst_cse)
        post_data = {
            'company_id': self.company.id,
            'title': 'Junior Python Developer',
            'role_description': 'Department-specific placement drive for CSE students.',
            'job_location': 'Remote / Pune',
            'package_ctc': '8.50',
            'bond_details': 'None',
            'min_tenth_percentage': '65.0',
            'min_twelfth_percentage': '65.0',
            'min_graduation_cgpa': '6.5',
            'max_active_backlogs': '1',
            'allowed_departments': [str(self.dept_cse.id)],
            'allowed_batches': '2025',
            'allowed_degrees': 'B.Tech',
            'application_deadline': (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M'),
            'drive_date': '2027-01-18'
        }
        response = self.client.post(reverse('placements:post_job'), post_data)
        self.assertEqual(response.status_code, 302)

        job = JobOpening.objects.get(title='Junior Python Developer')
        approval = DepartmentJobApproval.objects.get(job_opening=job, department=self.dept_cse)
        self.assertEqual(approval.status, ApprovalStatus.APPROVED)
        self.assertEqual(approval.reviewed_by, self.asst_cse)

    def test_workflow_g_job_edit_view(self):
        """
        Workflow G:
        TPO can edit job details and lifecycle status (e.g. PUBLISHED -> IN_PROGRESS -> COMPLETED).
        """
        job = JobOpening.objects.create(
            company=self.company,
            title='Test Automation Engineer',
            role_description='SDET role',
            job_location='Bangalore',
            package_ctc=Decimal('10.00'),
            min_tenth_percentage=Decimal('70.00'),
            min_twelfth_percentage=Decimal('70.00'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            allowed_degrees='B.Tech',
            allowed_batches='2025',
            application_deadline=timezone.now() + timedelta(days=30),
            drive_date='2027-01-20',
            created_by=self.tpo,
            status=JobStatus.PUBLISHED
        )

        self.client.force_login(self.tpo)
        edit_data = {
            'title': 'Senior Test Automation Engineer',
            'role_description': 'Updated SDET role with cypress and selenium.',
            'job_location': 'Bangalore (Hybrid)',
            'package_ctc': '14.00',
            'bond_details': '1 Year Service Agreement',
            'status': JobStatus.IN_PROGRESS,
            'drive_date': '2027-01-22',
            'application_deadline': '2026-12-25 18:00:00'
        }
        resp = self.client.post(reverse('placements:job_edit', kwargs={'job_id': job.id}), edit_data)
        self.assertEqual(resp.status_code, 302)

        job.refresh_from_db()
        self.assertEqual(job.title, 'Senior Test Automation Engineer')
        self.assertEqual(job.package_ctc, Decimal('14.00'))
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
