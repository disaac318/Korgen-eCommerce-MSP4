from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase, override_settings
from django.test import TestCase

from accounts.models import Account
from category.models import Category
from store.models import Product
from .models import Cart, CartItem
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


class CartItemQuantityConstraintTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Cart',
            last_name='Buyer',
            email='cart-buyer@example.com',
            username='cart-buyer',
            password='test-pass-12345',
        )
        self.category = Category.objects.create(
            category_name='Cart Category',
            slug='cart-category',
        )
        self.product = Product.objects.create(
            product_name='Cart Product',
            slug='cart-product',
            description='Cart product',
            price=Decimal('10.00'),
            images='photos/products/cart-product.jpg',
            stock=5,
            category=self.category,
        )
        self.cart = Cart.objects.create(cart_id='test-cart')

    def test_cart_item_quantity_must_be_at_least_one(self):
        cart_item = CartItem(
            user=self.user,
            product=self.product,
            cart=self.cart,
            quantity=0,
        )

        with self.assertRaises(ValidationError):
            cart_item.full_clean()

    def test_database_rejects_zero_quantity_cart_items(self):
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                user=self.user,
                product=self.product,
                cart=self.cart,
                quantity=0,
            )
