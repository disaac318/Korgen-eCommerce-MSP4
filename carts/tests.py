from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from .pricing import calculate_cart_totals, calculate_delivery_total


@override_settings(
    DELIVERY_FLAT_RATE='3.99',
    DELIVERY_FREE_THRESHOLD='50.00',
)
class PricingTests(SimpleTestCase):
    def test_delivery_is_flat_rate_below_free_threshold(self):
        self.assertEqual(
            calculate_delivery_total(Decimal('49.99')),
            Decimal('3.99'),
        )

    def test_delivery_is_free_at_threshold(self):
        self.assertEqual(
            calculate_delivery_total(Decimal('50.00')),
            Decimal('0.00'),
        )

    def test_cart_totals_include_delivery_in_grand_total(self):
        cart_items = [
            SimpleNamespace(
                quantity=2,
                sub_total=lambda: Decimal('20.00'),
            ),
        ]

        totals = calculate_cart_totals(cart_items)

        self.assertEqual(totals['total'], Decimal('20.00'))
        self.assertEqual(totals['tax'], Decimal('4.00'))
        self.assertEqual(totals['delivery_total'], Decimal('3.99'))
        self.assertEqual(totals['grand_total'], Decimal('27.99'))
        self.assertEqual(totals['quantity'], 2)
