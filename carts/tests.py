from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase, override_settings
from django.test import TestCase
from django.urls import reverse

from accounts.models import Account, BillingDetails
from category.models import Category
from orders.models import Order, OrderProduct
from store.models import Product
from .models import Cart, CartItem
from .pricing import calculate_cart_totals, calculate_delivery_total


def create_active_user(
    email='cart-buyer@example.com',
    username='cart-buyer',
):
    user = Account.objects.create_user(
        first_name='Cart',
        last_name='Buyer',
        email=email,
        username=username,
        password='test-pass-12345',
    )
    user.is_active = True
    user.save(update_fields=['is_active'])
    return user


def create_product(
    name='Cart Product',
    slug='cart-product',
    stock=5,
    price=Decimal('10.00'),
):
    category, _ = Category.objects.get_or_create(
        category_name='Cart Category',
        defaults={'slug': 'cart-category'},
    )
    return Product.objects.create(
        product_name=name,
        slug=slug,
        description='Cart product',
        price=price,
        images='photos/products/cart-product.jpg',
        stock=stock,
        category=category,
    )


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
        self.user = create_active_user()
        self.product = create_product()
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


class CartBehaviourTests(TestCase):
    def setUp(self):
        self.user = create_active_user()
        self.product = create_product()

    def create_user_cart_item(self, quantity=1):
        return CartItem.objects.create(
            user=self.user,
            product=self.product,
            cart=Cart.objects.create(cart_id='user-cart'),
            quantity=quantity,
        )

    def test_guest_can_add_product_to_cart(self):
        response = self.client.get(
            reverse('add_cart', kwargs={'product_id': self.product.id}),
        )

        self.assertRedirects(response, reverse('cart'))
        cart_item = CartItem.objects.get(product=self.product)
        self.assertIsNone(cart_item.user)
        self.assertEqual(cart_item.quantity, 1)

    def test_authenticated_user_can_add_product_to_cart(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('add_cart', kwargs={'product_id': self.product.id}),
        )

        self.assertRedirects(response, reverse('cart'))
        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 1)

    def test_increment_cart_item_increases_quantity(self):
        self.client.force_login(self.user)
        cart_item = self.create_user_cart_item(quantity=1)

        response = self.client.get(
            reverse('increment_cart_item', kwargs={
                'cart_item_id': cart_item.id,
            }),
        )

        self.assertRedirects(response, reverse('cart'))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    def test_remove_from_cart_decreases_quantity(self):
        self.client.force_login(self.user)
        cart_item = self.create_user_cart_item(quantity=2)

        response = self.client.post(
            reverse('remove_from_cart', kwargs={
                'cart_item_id': cart_item.id,
            }),
        )

        self.assertRedirects(response, reverse('cart'))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)

    def test_remove_from_cart_deletes_item_when_quantity_is_one(self):
        self.client.force_login(self.user)
        cart_item = self.create_user_cart_item(quantity=1)

        response = self.client.post(
            reverse('remove_from_cart', kwargs={
                'cart_item_id': cart_item.id,
            }),
        )

        self.assertRedirects(response, reverse('cart'))
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_delete_cart_item_removes_entire_item(self):
        self.client.force_login(self.user)
        cart_item = self.create_user_cart_item(quantity=3)

        response = self.client.post(
            reverse('delete_cart_item', kwargs={
                'cart_item_id': cart_item.id,
            }),
        )

        self.assertRedirects(response, reverse('cart'))
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_login_merges_matching_guest_cart_item_into_user_cart(self):
        guest_cart = Cart.objects.create(cart_id='guest-cart')
        CartItem.objects.create(
            cart=guest_cart,
            product=self.product,
            quantity=2,
        )
        user_item = self.create_user_cart_item(quantity=1)
        session = self.client.session
        session['cart_id'] = guest_cart.cart_id
        session.save()
        self.client.force_login(self.user)

        response = self.client.get(reverse('cart'))

        self.assertEqual(response.status_code, 200)
        user_item.refresh_from_db()
        self.assertEqual(user_item.quantity, 3)
        self.assertFalse(
            CartItem.objects.filter(
                cart=guest_cart,
                user__isnull=True,
            ).exists(),
        )


@override_settings(
    DELIVERY_FLAT_RATE='3.99',
    DELIVERY_FREE_THRESHOLD='50.00',
)
class CheckoutOrderCreationTests(TestCase):
    def setUp(self):
        self.user = create_active_user()
        self.product = create_product(price=Decimal('12.50'))
        self.cart = Cart.objects.create(cart_id='checkout-cart')
        self.cart_item = CartItem.objects.create(
            user=self.user,
            product=self.product,
            cart=self.cart,
            quantity=2,
        )
        self.checkout_data = {
            'first_name': 'Checkout',
            'last_name': 'Buyer',
            'email': 'checkout-buyer@example.com',
            'phone': '07123456789',
            'address_line_1': '1 Checkout Street',
            'address_line_2': '',
            'county': 'London',
            'postcode': 'CH1 1AA',
            'country': 'United Kingdom',
            'order_notes': 'Leave with reception.',
        }

    def test_checkout_requires_cart_items(self):
        self.client.force_login(self.user)
        CartItem.objects.filter(user=self.user).delete()

        response = self.client.get(reverse('checkout'))

        self.assertRedirects(response, reverse('cart'))

    def test_checkout_creates_pending_order_from_cart_items(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('checkout'), self.checkout_data)

        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse('orders:payment', kwargs={
                'order_number': order.order_number,
            }),
            fetch_redirect_response=False,
        )
        self.assertFalse(order.is_ordered)
        self.assertEqual(order.order_total, Decimal('25.00'))
        self.assertEqual(order.tax, Decimal('5.00'))
        self.assertEqual(order.delivery_total, Decimal('3.99'))
        self.assertEqual(order.grand_total, Decimal('33.99'))
        self.assertEqual(order.first_name, self.checkout_data['first_name'])
        self.assertEqual(order.email, self.checkout_data['email'])
        self.assertEqual(order.country, self.checkout_data['country'])

    def test_checkout_copies_cart_items_to_order_products(self):
        self.client.force_login(self.user)

        self.client.post(reverse('checkout'), self.checkout_data)

        order_product = OrderProduct.objects.get(
            order__user=self.user,
            product=self.product,
        )
        self.assertEqual(order_product.quantity, 2)
        self.assertEqual(order_product.product_price, self.product.price)
        self.assertFalse(order_product.ordered)

    def test_checkout_saves_billing_details_for_future_orders(self):
        self.client.force_login(self.user)

        self.client.post(reverse('checkout'), self.checkout_data)

        billing_details = BillingDetails.objects.get(user=self.user)
        self.assertEqual(
            billing_details.address_line_1,
            self.checkout_data['address_line_1'],
        )
        self.assertEqual(billing_details.email, self.checkout_data['email'])
        self.assertEqual(billing_details.postcode, self.checkout_data['postcode'])
        self.assertEqual(billing_details.country, self.checkout_data['country'])

    def test_checkout_prefills_saved_billing_details(self):
        BillingDetails.objects.create(
            user=self.user,
            first_name='Saved',
            last_name='Customer',
            email='saved@example.com',
            phone='07987654321',
            address_line_1='2 Saved Street',
            address_line_2='Flat 4',
            county='Manchester',
            postcode='SV1 2ED',
            country='United Kingdom',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_saved_billing_details'])
        form = response.context['form']
        self.assertContains(response, 'id_country')
        self.assertEqual(form.initial['first_name'], 'Saved')
        self.assertEqual(form.initial['email'], 'saved@example.com')
        self.assertEqual(form.initial['address_line_1'], '2 Saved Street')
        self.assertEqual(form.initial['country'], 'United Kingdom')
