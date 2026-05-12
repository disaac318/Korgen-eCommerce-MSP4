from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account


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
