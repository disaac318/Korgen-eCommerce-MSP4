from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .views import _build_stripe_checkout_session_payload


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
