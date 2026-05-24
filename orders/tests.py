from decimal import Decimal
import builtins
from unittest.mock import MagicMock, patch
import sys
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import Account
from category.models import Category
from store.models import Product
from .models import Order, OrderProduct, Payment
from .views import (
    InsufficientStockError,
    _build_stripe_checkout_session_payload,
    _mark_order_paid,
)


class StripeCheckoutPayloadTests(SimpleTestCase):
    def test_checkout_payload_uses_card_only_and_does_not_save_cards(self):
        order = SimpleNamespace(
            order_number='ORDER123',
            email='buyer@example.com',
            grand_total=Decimal('12.34'),
        )

        payload = _build_stripe_checkout_session_payload(
            order,
            'https://example.com/success',
            'https://example.com/cancel',
        )

        self.assertEqual(payload['mode'], 'payment')
        self.assertEqual(payload['payment_method_types[0]'], 'card')
        self.assertEqual(payload['customer_email'], 'buyer@example.com')
        self.assertNotIn('customer', payload)
        self.assertNotIn('customer_creation', payload)
        self.assertNotIn('payment_intent_data[setup_future_usage]', payload)
        self.assertNotIn(
            'saved_payment_method_options[payment_method_save]',
            payload,
        )


class InvoiceViewTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Invoice',
            last_name='Buyer',
            email='invoice-buyer@example.com',
            username='invoice-buyer',
            password='test-pass-12345',
        )
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])

        self.other_user = Account.objects.create_user(
            first_name='Other',
            last_name='Buyer',
            email='other-invoice-buyer@example.com',
            username='other-invoice-buyer',
            password='test-pass-12345',
        )
        self.other_user.is_active = True
        self.other_user.save(update_fields=['is_active'])

        self.category = Category.objects.create(
            category_name='Invoice Category',
            slug='invoice-category',
        )
        self.product = Product.objects.create(
            product_name='Invoice Product',
            slug='invoice-product',
            description='Invoice product',
            price=Decimal('10.00'),
            images='photos/products/invoice.jpg',
            stock=5,
            category=self.category,
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name='Invoice',
            last_name='Buyer',
            email='invoice-buyer@example.com',
            phone='07123456789',
            address_line_1='1 Invoice Street',
            county='London',
            postcode='I1 1AA',
            order_total=Decimal('10.00'),
            tax=Decimal('2.00'),
            delivery_total=Decimal('3.99'),
            grand_total=Decimal('15.99'),
            is_ordered=True,
        )
        OrderProduct.objects.create(
            order=self.order,
            user=self.user,
            product=self.product,
            quantity=1,
            product_price=Decimal('10.00'),
            ordered=True,
        )

    def test_owner_can_view_paid_order_invoice(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('orders:invoice', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'INV-{self.order.order_number}')
        self.assertContains(response, 'Invoice Product')

    def test_pending_order_invoice_is_not_available(self):
        self.order.is_ordered = False
        self.order.save(update_fields=['is_ordered'])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('orders:invoice', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_view_invoice(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse('orders:invoice', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_download_paid_order_invoice_pdf(self):
        self.client.force_login(self.user)
        html_mock = MagicMock()
        html_mock.return_value.write_pdf.return_value = b'%PDF-1.7 test'
        fake_weasyprint = SimpleNamespace(HTML=html_mock)

        with patch.dict(sys.modules, {'weasyprint': fake_weasyprint}):
            response = self.client.get(
                reverse('orders:invoice_pdf', kwargs={
                    'order_number': self.order.order_number,
                }),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(
            response['Content-Disposition'],
            (
                'attachment; '
                f'filename="invoice-{self.order.order_number}.pdf"'
            ),
        )
        self.assertEqual(response.content, b'%PDF-1.7 test')

    def test_invoice_pdf_returns_503_when_weasyprint_is_not_installed(self):
        self.client.force_login(self.user)

        with patch.dict(sys.modules, {'weasyprint': None}):
            response = self.client.get(
                reverse('orders:invoice_pdf', kwargs={
                    'order_number': self.order.order_number,
                }),
            )

        self.assertEqual(response.status_code, 503)

    def test_invoice_pdf_returns_503_when_weasyprint_system_libs_are_missing(self):
        self.client.force_login(self.user)
        original_import = builtins.__import__

        def import_with_missing_system_libs(name, *args, **kwargs):
            if name == 'weasyprint':
                raise OSError('missing native library')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=import_with_missing_system_libs):
            response = self.client.get(
                reverse('orders:invoice_pdf', kwargs={
                    'order_number': self.order.order_number,
                }),
            )

        self.assertEqual(response.status_code, 503)


class StockDeductionTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Stock',
            last_name='Buyer',
            email='stock-buyer@example.com',
            username='stock-buyer',
            password='test-pass-12345',
        )
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])

        self.category = Category.objects.create(
            category_name='Stock Category',
            slug='stock-category',
        )
        self.product = Product.objects.create(
            product_name='Stock Product',
            slug='stock-product',
            description='Stock product',
            price=Decimal('10.00'),
            images='photos/products/stock.jpg',
            stock=5,
            category=self.category,
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name='Stock',
            last_name='Buyer',
            email='stock-buyer@example.com',
            phone='07123456789',
            address_line_1='1 Stock Street',
            county='London',
            postcode='S1 1AA',
            order_total=Decimal('20.00'),
            tax=Decimal('4.00'),
            delivery_total=Decimal('0.00'),
            grand_total=Decimal('24.00'),
            is_ordered=False,
        )
        OrderProduct.objects.create(
            order=self.order,
            user=self.user,
            product=self.product,
            quantity=2,
            product_price=Decimal('10.00'),
            ordered=False,
        )
        self.payment = Payment.objects.create(
            user=self.user,
            payment_id='stock-payment-1',
            payment_method='Test',
            amount_paid=Decimal('24.00'),
            status=Payment.STATUS_COMPLETED,
        )

    def test_mark_order_paid_deducts_stock_once(self):
        _mark_order_paid(self.order, self.payment)
        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 3)
        self.assertTrue(self.order.is_ordered)
        self.assertTrue(self.order.stock_deducted)

        _mark_order_paid(self.order, self.payment)
        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 3)

    def test_mark_order_paid_fails_when_stock_is_too_low(self):
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        with self.assertRaises(InsufficientStockError):
            _mark_order_paid(self.order, self.payment)

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 1)
        self.assertFalse(self.order.is_ordered)
        self.assertFalse(self.order.stock_deducted)


class PaymentErrorHandlingTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Payment',
            last_name='Buyer',
            email='payment-buyer@example.com',
            username='payment-buyer',
            password='test-pass-12345',
        )
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])

        self.category = Category.objects.create(
            category_name='Payment Category',
            slug='payment-category',
        )
        self.product = Product.objects.create(
            product_name='Payment Product',
            slug='payment-product',
            description='Payment product',
            price=Decimal('10.00'),
            images='photos/products/payment.jpg',
            stock=5,
            category=self.category,
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name='Payment',
            last_name='Buyer',
            email='payment-buyer@example.com',
            phone='07123456789',
            address_line_1='1 Payment Street',
            county='London',
            postcode='P1 1AA',
            order_total=Decimal('20.00'),
            tax=Decimal('4.00'),
            delivery_total=Decimal('0.00'),
            grand_total=Decimal('24.00'),
            is_ordered=False,
        )
        self.order_product = OrderProduct.objects.create(
            order=self.order,
            user=self.user,
            product=self.product,
            quantity=2,
            product_price=Decimal('10.00'),
            ordered=False,
        )
        self.client.force_login(self.user)

    @override_settings(STRIPE_PUBLIC_KEY='', STRIPE_SECRET_KEY='')
    def test_stripe_checkout_returns_503_when_credentials_are_missing(self):
        response = self.client.post(
            reverse('orders:create_stripe_checkout_session', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()['error'],
            'Stripe credentials are not configured.',
        )

    @override_settings(PAYPAL_CLIENT_ID='', PAYPAL_CLIENT_SECRET='')
    def test_paypal_create_order_returns_503_when_credentials_are_missing(self):
        response = self.client.post(
            reverse('orders:create_paypal_order', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()['error'],
            'PayPal credentials are not configured.',
        )

    @override_settings(
        STRIPE_PUBLIC_KEY='pk_test_example',
        STRIPE_SECRET_KEY='sk_test_example',
    )
    def test_stripe_checkout_returns_400_when_stock_is_too_low(self):
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        response = self.client.post(
            reverse('orders:create_stripe_checkout_session', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Payment Product has only 1 in stock.', response.json()['error'])

    @override_settings(
        PAYPAL_CLIENT_ID='paypal-client-id',
        PAYPAL_CLIENT_SECRET='paypal-client-secret',
    )
    def test_paypal_create_order_returns_400_when_stock_is_too_low(self):
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        response = self.client.post(
            reverse('orders:create_paypal_order', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Payment Product has only 1 in stock.', response.json()['error'])

    def test_payment_page_redirects_to_cart_when_stock_is_too_low(self):
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        response = self.client.get(
            reverse('orders:payment', kwargs={
                'order_number': self.order.order_number,
            }),
        )

        self.assertRedirects(response, reverse('cart'))
