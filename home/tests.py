from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from category.models import Category
from store.models import Product


class IndexViewTests(TestCase):
    def test_product_cards_do_not_render_raw_template_tags(self):
        category = Category.objects.create(
            category_name='Electronics',
            slug='electronics',
        )
        Product.objects.create(
            product_name='Action Camera',
            slug='action-camera',
            description='Compact travel video camera.',
            price='199.99',
            images='photos/products/action-camera.jpg',
            stock=5,
            is_available=True,
            category=category,
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Action Camera')
        self.assertContains(response, 'Add to cart')
        self.assertNotContains(response, '{{')
        self.assertNotContains(response, '}}')
        self.assertNotContains(response, '{%')
        self.assertNotContains(response, '%}')


class ContactViewTests(TestCase):
    def test_contact_page_renders(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contact Korgen')
        self.assertContains(response, 'info@korgen.com')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        CONTACT_EMAIL='support@example.com',
        DEFAULT_FROM_EMAIL='no-reply@example.com',
    )
    def test_valid_contact_form_sends_email(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Tony Stark',
                'email': 'tony@example.com',
                'subject': 'Order question',
                'message': 'Please help with my recent order.',
            },
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['support@example.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['tony@example.com'])
        self.assertIn('Tony Stark', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_invalid_contact_form_does_not_send_email(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': '',
                'email': 'not-an-email',
                'subject': '',
                'message': 'Short',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
