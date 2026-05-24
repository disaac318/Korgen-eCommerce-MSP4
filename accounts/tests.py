from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account


class RegistrationEmailTests(TestCase):
    def test_registration_sends_activation_email(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'Email',
            'last_name': 'User',
            'email': 'email-user@example.com',
            'username': 'emailuser',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['email-user@example.com'])
        self.assertIn('/accounts/activate/', mail.outbox[0].body)

        user = Account.objects.get(email='email-user@example.com')
        self.assertFalse(user.is_active)

    @override_settings(
        DEVELOPMENT=False,
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    )
    def test_registration_fails_if_production_uses_console_email_backend(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'Console',
            'last_name': 'User',
            'email': 'console-user@example.com',
            'username': 'consoleuser',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Account.objects.filter(email='console-user@example.com').exists(),
        )
        self.assertContains(
            response,
            'We could not send your activation email.',
        )


class AnonymousOnlyAuthPageTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Active',
            last_name='User',
            email='active@example.com',
            username='activeuser',
            password='test-pass-12345',
        )
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])
        self.client.force_login(self.user)

    def test_authenticated_user_cannot_access_register_page(self):
        response = self.client.get(reverse('accounts:register'))

        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_authenticated_user_cannot_access_login_page(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertRedirects(response, reverse('accounts:dashboard'))


@override_settings(REMEMBER_ME_SESSION_AGE=1209600)
class LoginRememberMeTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Test',
            last_name='User',
            email='remember@example.com',
            username='remember',
            password='test-pass-12345',
        )
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])

    def test_login_without_remember_me_expires_when_browser_closes(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'remember@example.com',
            'password': 'test-pass-12345',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_with_remember_me_uses_configured_session_age(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': 'remember@example.com',
            'password': 'test-pass-12345',
            'remember': '1',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session.get_expiry_age(),
            settings.REMEMBER_ME_SESSION_AGE,
        )
        self.assertFalse(self.client.session.get_expire_at_browser_close())
