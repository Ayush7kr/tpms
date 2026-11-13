from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.students.models import StudentProfile


class DepartmentScopingTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.dept_cse = Department.objects.create(code='CSE', name='Computer Science')
        self.dept_mech = Department.objects.create(code='MECH', name='Mechanical')

        self.assistant = User.objects.create_user(
            email='assistant.cse@apex.edu.in',
            password='Password@123',
            first_name='Assistant',
            last_name='CSE',
            role=UserRole.TNP_ASSISTANT
        )
        # Allocate only CSE to this assistant
        AssistantDepartmentAssignment.objects.create(
            assistant=self.assistant,
            department=self.dept_cse
        )

        # CSE Student
        u_cse = User.objects.create_user(email='cse.student@apex.edu.in', password='pwd', first_name='CSE', last_name='Student', role=UserRole.STUDENT)
        self.student_cse = StudentProfile.objects.create(
            user=u_cse,
            department=self.dept_cse,
            roll_number='21CSE999',
            prn_number='PRN999',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('80.00'),
            twelfth_percentage=Decimal('80.00'),
            graduation_cgpa=Decimal('8.00')
        )

        # MECH Student
        u_mech = User.objects.create_user(email='mech.student@apex.edu.in', password='pwd', first_name='MECH', last_name='Student', role=UserRole.STUDENT)
        self.student_mech = StudentProfile.objects.create(
            user=u_mech,
            department=self.dept_mech,
            roll_number='21ME999',
            prn_number='PRN998',
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('70.00'),
            twelfth_percentage=Decimal('70.00'),
            graduation_cgpa=Decimal('7.00')
        )

    def test_assistant_roster_only_shows_assigned_department(self):
        """Assistant can only see student records from their assigned department."""
        self.client.force_login(self.assistant)
        response = self.client.get(reverse('assistant_panel:student_roster'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '21CSE999')
        self.assertNotContains(response, '21ME999')

    def test_assistant_cannot_edit_unassigned_department_student(self):
        """Assistant cannot edit students outside their department (HTTP 404 / access blocked)."""
        self.client.force_login(self.assistant)
        response = self.client.get(reverse('assistant_panel:student_edit', args=[self.student_mech.id]))
        self.assertEqual(response.status_code, 404)
