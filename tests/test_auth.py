from django.test import TestCase, Client, override_settings
from django.urls import reverse
from apps.accounts.models import User, UserRole


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test.student@apex.edu.in',
            password='Password@123',
            first_name='Test',
            last_name='Student',
            role=UserRole.STUDENT
        )

    def test_password_is_cryptographically_hashed(self):
        """Verify that user passwords are never stored in plain text."""
        self.assertNotEqual(self.user.password, 'Password@123')
        self.assertTrue(self.user.check_password('Password@123'))
        self.assertFalse(self.user.check_password('WrongPassword'))

    def test_custom_login_success(self):
        """Verify custom email-based authentication view."""
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test.student@apex.edu.in',
            'password': 'Password@123'
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_custom_login_invalid_password(self):
        """Verify login failure with incorrect credentials."""
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test.student@apex.edu.in',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid credentials')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_deactivated_user_cannot_login(self):
        """Verify deactivated accounts cannot authenticate."""
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test.student@apex.edu.in',
            'password': 'Password@123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deactivated')
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_login_auto_redirects_by_role(self):
        """Verify that any authenticated user is automatically dispatched to their designated portal without manual role selection."""
        roles_and_targets = [
            (UserRole.ADMIN, reverse('admin_panel:dashboard')),
            (UserRole.PRINCIPAL, reverse('principal_panel:dashboard')),
            (UserRole.TNP_OFFICER, reverse('tpo_panel:dashboard')),
            (UserRole.TNP_ASSISTANT, reverse('assistant_panel:dashboard')),
            (UserRole.STUDENT, reverse('student_panel:dashboard')),
        ]
        for role, expected_target in roles_and_targets:
            u = User.objects.create_user(
                email=f'user.{role.lower()}@apex.edu.in',
                password='Password@123',
                first_name=role.capitalize(),
                last_name='User',
                role=role
            )
            resp = self.client.post(reverse('accounts:login'), {
                'email': u.email,
                'password': 'Password@123'
            }, follow=False)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.url, expected_target)
            self.client.logout()

    @override_settings(DEMO_MODE=False)
    def test_login_page_renders_cleanly_without_demo_artifacts(self):
        """Verify that login page does not expose demo passwords or unrelated project emails."""
        resp = self.client.get(reverse('accounts:login'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'hirescan')
        self.assertNotContains(resp, 'apex@123')
        self.assertNotContains(resp, 'Mentor Demo Tools')
        self.assertNotContains(resp, 'Autofill')
        self.assertNotContains(resp, 'Instant Direct Login')
        self.assertContains(resp, 'Your placement season, in one place.')

