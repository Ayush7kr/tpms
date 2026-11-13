from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from apps.accounts.models import User, UserRole
from apps.departments.models import Department
from apps.students.models import StudentProfile, PlacementStatus
from apps.placements.models import JobOpening, JobStatus
from apps.companies.models import Company, CompanyTier
from apps.career_assistant.models import Conversation, ChatMessage
from apps.career_assistant.services.ai_service import AICareerAssistantService
from apps.career_assistant.services.context_builder import StudentCareerContextBuilder


class AICareerAssistantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Academic Department
        cls.dept = Department.objects.create(code='CSE', name='Computer Science & Engineering')
        cls.dept_ece = Department.objects.create(code='ECE', name='Electronics & Communication')

        # Student Alpha
        cls.user_alpha = User.objects.create_user(
            email='alpha@apex.edu.in',
            password='Password123!',
            first_name='Alpha',
            last_name='Student',
            role=UserRole.STUDENT
        )
        cls.profile_alpha = StudentProfile.objects.create(
            user=cls.user_alpha,
            department=cls.dept,
            roll_number='21CSE001',
            prn_number='PRN21001',
            batch_year=2025,
            graduation_cgpa=Decimal('8.50'),
            tenth_percentage=Decimal('88.00'),
            twelfth_percentage=Decimal('86.00'),
            active_backlogs=0,
            skills='Python, Django, React, PostgreSQL',
            placement_status=PlacementStatus.UNPLACED
        )

        # Student Beta
        cls.user_beta = User.objects.create_user(
            email='beta@apex.edu.in',
            password='Password123!',
            first_name='Beta',
            last_name='Student',
            role=UserRole.STUDENT
        )
        cls.profile_beta = StudentProfile.objects.create(
            user=cls.user_beta,
            department=cls.dept_ece,
            roll_number='21ECE002',
            prn_number='PRN21002',
            batch_year=2025,
            graduation_cgpa=Decimal('7.20'),
            tenth_percentage=Decimal('80.00'),
            twelfth_percentage=Decimal('78.00'),
            active_backlogs=1,
            skills='C++, Embedded C, MATLAB',
            placement_status=PlacementStatus.UNPLACED
        )

        # Non-Student User (TPO)
        cls.tpo_user = User.objects.create_user(
            email='tpo_test@apex.edu.in',
            password='Password123!',
            first_name='Vikram',
            last_name='TPO',
            role=UserRole.TNP_OFFICER
        )

        # Hiring Partner & Drive
        cls.company = Company.objects.create(
            name='Deloitte India',
            industry_sector='Consulting & Cloud',
            tier=CompanyTier.TIER_1_DREAM,
            contact_person='HR Lead',
            contact_email='hr@deloitte.com'
        )
        from django.utils import timezone
        import datetime
        cls.drive = JobOpening.objects.create(
            company=cls.company,
            title='Associate Analyst - Cloud Architecture',
            role_description='Design cloud infrastructure and automate enterprise microservices.',
            job_location='Hyderabad / Bangalore',
            package_ctc=Decimal('9.50'),
            min_graduation_cgpa=Decimal('7.00'),
            max_active_backlogs=0,
            application_deadline=timezone.now() + datetime.timedelta(days=14),
            drive_date=timezone.now().date() + datetime.timedelta(days=20),
            status=JobStatus.PUBLISHED
        )
        cls.drive.allowed_departments.add(cls.dept)

    def setUp(self):
        self.client_alpha = Client()
        self.client_alpha.login(email='alpha@apex.edu.in', password='Password123!')

        self.client_beta = Client()
        self.client_beta.login(email='beta@apex.edu.in', password='Password123!')

        self.client_tpo = Client()
        self.client_tpo.login(email='tpo_test@apex.edu.in', password='Password123!')

    def test_unauthenticated_cannot_access_career_assistant(self):
        anon = Client()
        url = reverse('career_assistant:career_assistant')
        response = anon.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_non_student_cannot_access_career_assistant(self):
        url = reverse('career_assistant:career_assistant')
        response = self.client_tpo.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.tpo_user.get_dashboard_url())

    def test_student_can_access_career_assistant(self):
        url = reverse('career_assistant:career_assistant')
        response = self.client_alpha.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Career &amp; Placement Assistant')
        self.assertContains(response, 'Alpha')

        # Assert default conversation was created
        conv = Conversation.objects.filter(student=self.profile_alpha).first()
        self.assertIsNotNone(conv)
        self.assertEqual(conv.messages.count(), 1)

    def test_student_chat_api_success(self):
        conv = Conversation.objects.create(student=self.profile_alpha, title='Placement Guidance')
        url = reverse('career_assistant:chat_api')

        response = self.client_alpha.post(
            url,
            data={'conversation_id': conv.id, 'message': 'What skills do I need to learn to become a Full Stack Developer?'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Personalized Skill-Gap Analysis for Alpha Student', data['reply'])
        self.assertIn('Python', data['reply'])

        # Check DB persistence
        self.assertEqual(conv.messages.filter(sender='STUDENT').count(), 1)
        self.assertEqual(conv.messages.filter(sender='ASSISTANT').count(), 1)

    def test_student_cannot_access_other_student_conversation(self):
        # Conversation owned by Alpha
        conv_alpha = Conversation.objects.create(student=self.profile_alpha, title='Alpha Secret Chat')

        # Beta attempts to post to Alpha's conversation
        url = reverse('career_assistant:chat_api')
        response = self.client_beta.post(
            url,
            data={'conversation_id': conv_alpha.id, 'message': 'Trying to snoop on Alpha'}
        )
        self.assertEqual(response.status_code, 404)

        # Beta attempts to view Alpha's conversation
        view_url = reverse('career_assistant:career_assistant_detail', kwargs={'conversation_id': conv_alpha.id})
        view_response = self.client_beta.get(view_url)
        self.assertEqual(view_response.status_code, 404)

    def test_student_cannot_delete_other_student_conversation(self):
        conv_alpha = Conversation.objects.create(student=self.profile_alpha, title='Alpha Chat to Protect')
        del_url = reverse('career_assistant:delete_conversation', kwargs={'conversation_id': conv_alpha.id})

        response = self.client_beta.post(del_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Conversation.objects.filter(id=conv_alpha.id).exists())

    def test_empty_message_rejected(self):
        conv = Conversation.objects.create(student=self.profile_alpha, title='Test Session')
        url = reverse('career_assistant:chat_api')
        response = self.client_alpha.post(url, data={'conversation_id': conv.id, 'message': '   '})
        self.assertEqual(response.status_code, 400)

    def test_message_length_limit_enforced(self):
        conv = Conversation.objects.create(student=self.profile_alpha, title='Test Session')
        url = reverse('career_assistant:chat_api')
        long_message = 'A' * 2005
        response = self.client_alpha.post(url, data={'conversation_id': conv.id, 'message': long_message})
        self.assertEqual(response.status_code, 400)

    def test_company_specific_guidance_uses_real_drive_data(self):
        conv = Conversation.objects.create(student=self.profile_alpha, title='Company Prep Session')
        reply = AICareerAssistantService.generate_response(conv, 'What should I prepare for the Deloitte drive?')
        self.assertIn('Deloitte India', reply)
        self.assertIn('9.5 LPA', reply)
        self.assertIn('Alpha Student', reply)

    def test_roadmap_generation_structured_breakdown(self):
        conv = Conversation.objects.create(student=self.profile_alpha, title='Roadmap Session')
        reply = AICareerAssistantService.generate_response(conv, 'Create a 30-day Full Stack Developer preparation roadmap.')
        self.assertIn('30-Day Strategic Placement Preparation Roadmap', reply)
        self.assertIn('Week 1', reply)
        self.assertIn('Week 2', reply)
        self.assertIn('Week 3', reply)
        self.assertIn('Week 4', reply)

    def test_context_builder_privacy_and_isolation(self):
        # Alpha context has Alpha details only
        ctx_alpha = StudentCareerContextBuilder.build_context(self.profile_alpha)
        self.assertEqual(ctx_alpha['student']['name'], 'Alpha Student')
        self.assertEqual(ctx_alpha['student']['graduation_cgpa'], 8.50)
        self.assertIn('Python', ctx_alpha['student']['skills'])

        # Beta context has Beta details only
        ctx_beta = StudentCareerContextBuilder.build_context(self.profile_beta)
        self.assertEqual(ctx_beta['student']['name'], 'Beta Student')
        self.assertEqual(ctx_beta['student']['graduation_cgpa'], 7.20)
        self.assertNotIn('Python', ctx_beta['student']['skills'])
        self.assertIn('C++', ctx_beta['student']['skills'])

    @patch('apps.career_assistant.services.ai_service.AICareerAssistantService._call_gemini_api')
    @patch('apps.career_assistant.services.ai_service.AICareerAssistantService.get_api_key')
    def test_mocked_gemini_api_call(self, mock_key, mock_call):
        mock_key.return_value = 'mock-test-key-12345'
        mock_call.return_value = 'Mocked Gemini AI placement response: Master trees, graph algorithms and system design.'

        conv = Conversation.objects.create(student=self.profile_alpha, title='Gemini Test')
        reply = AICareerAssistantService.generate_response(conv, 'Give me tips for technical interviews.')

        self.assertEqual(reply, 'Mocked Gemini AI placement response: Master trees, graph algorithms and system design.')
        mock_call.assert_called_once()

    def test_student_dashboard_has_clickable_drive_link(self):
        url = reverse('student_panel:dashboard')
        response = self.client_alpha.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'drive-link')
        self.assertContains(response, reverse('placements:drive_detail', kwargs={'job_id': self.drive.id}))
