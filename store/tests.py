from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Account, UserProfile
from category.models import Category
from orders.models import Order, OrderProduct

from .models import Product, ReviewRating, Variation


def create_active_user(
    email='review-buyer@example.com',
    username='review-buyer',
):
    user = Account.objects.create_user(
        first_name='Review',
        last_name='Buyer',
        email=email,
        username=username,
        password='test-pass-12345',
    )
    user.is_active = True
    user.save(update_fields=['is_active'])
    UserProfile.objects.create(user=user)
    return user


def create_category(name='Electronics', slug='electronics'):
    return Category.objects.create(
        category_name=name,
        slug=slug,
    )


def create_product(
    category,
    name='Action Camera',
    slug='action-camera',
    price=Decimal('199.99'),
):
    return Product.objects.create(
        product_name=name,
        slug=slug,
        description='Compact travel video camera.',
        price=price,
        images='photos/products/action-camera.jpg',
        stock=5,
        is_available=True,
        category=category,
    )


class SearchViewTests(TestCase):
    def setUp(self):
        self.category = create_category()
        self.name_match = create_product(self.category)
        self.description_match = Product.objects.create(
            product_name='Travel Backpack',
            slug='travel-backpack',
            description='Includes a padded camera compartment.',
            price='89.99',
            images='photos/products/travel-backpack.jpg',
            stock=3,
            is_available=True,
            category=self.category,
        )
        self.unavailable_match = Product.objects.create(
            product_name='Camera Strap',
            slug='camera-strap',
            description='Unavailable camera accessory.',
            price='14.99',
            images='photos/products/camera-strap.jpg',
            stock=0,
            is_available=False,
            category=self.category,
        )

    def test_search_matches_product_name_and_description(self):
        response = self.client.get(reverse('search'), {'keyword': 'camera'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.name_match.product_name)
        self.assertContains(response, self.description_match.product_name)
        self.assertNotContains(response, self.unavailable_match.product_name)
        self.assertEqual(response.context['product_count_label'], '2 items found.')

    def test_search_ignores_blank_keyword(self):
        response = self.client.get(reverse('search'), {'keyword': '   '})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['products'])
        self.assertEqual(response.context['product_count_label'], '0 items found.')


class StoreFilterTests(TestCase):
    def setUp(self):
        self.electronics = create_category()
        self.clothing = create_category('Clothing', 'clothing')
        self.camera = create_product(
            self.electronics,
            name='Action Camera',
            slug='action-camera',
            price=Decimal('199.99'),
        )
        self.shirt = create_product(
            self.clothing,
            name='Cotton Shirt',
            slug='cotton-shirt',
            price=Decimal('29.99'),
        )
        self.jacket = create_product(
            self.clothing,
            name='Winter Jacket',
            slug='winter-jacket',
            price=Decimal('149.99'),
        )
        Variation.objects.create(
            product=self.shirt,
            variation_category='size',
            variation_value='M',
        )
        Variation.objects.create(
            product=self.jacket,
            variation_category='size',
            variation_value='L',
        )

    def test_category_filter_returns_matching_products_only(self):
        response = self.client.get(
            reverse('products_by_category', kwargs={
                'category_slug': self.clothing.slug,
            }),
        )

        products = list(response.context['products'])
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.shirt, products)
        self.assertIn(self.jacket, products)
        self.assertNotIn(self.camera, products)
        self.assertEqual(response.context['product_count_label'], '2 items found.')

    def test_size_filter_returns_matching_products_only(self):
        response = self.client.get(reverse('store'), {'size': 'm'})

        products = list(response.context['products'])
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.shirt, products)
        self.assertNotIn(self.jacket, products)
        self.assertNotIn(self.camera, products)
        self.assertEqual(response.context['selected_size'], 'm')

    def test_price_filter_returns_products_inside_selected_range(self):
        response = self.client.get(
            reverse('store'),
            {
                'min_price': '100',
                'max_price': '200',
            },
        )

        products = list(response.context['products'])
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.camera, products)
        self.assertIn(self.jacket, products)
        self.assertNotIn(self.shirt, products)
        self.assertEqual(response.context['product_count_label'], '2 items found.')

    def test_invalid_price_filters_are_ignored_safely(self):
        response = self.client.get(
            reverse('store'),
            {
                'min_price': 'not-a-price',
                'max_price': '-5',
            },
        )

        products = list(response.context['products'])
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.camera, products)
        self.assertIn(self.shirt, products)
        self.assertIn(self.jacket, products)
        self.assertEqual(response.context['product_count_label'], '3 items found.')


class ProductDetailDisplayTests(TestCase):
    def setUp(self):
        category = create_category('Shirts', 'shirts')
        self.product = create_product(
            category,
            name='Catalog Shirt',
            slug='catalog-shirt',
        )
        self.product.images = 'photos/products/Coevals_JHte0VL.jpg'
        self.product.save(update_fields=['images'])
        Variation.objects.create(
            product=self.product,
            variation_category='color',
            variation_value='Burgundy',
        )

    def test_packaged_catalog_image_is_served_from_static_assets(self):
        self.assertEqual(
            self.product.display_image_url,
            '/static/images/products/Coevals.jpg',
        )

    def test_product_detail_renders_static_image_and_active_variation(self):
        response = self.client.get(
            reverse(
                'product_detail',
                kwargs={
                    'category_slug': self.product.category.slug,
                    'product_slug': self.product.slug,
                },
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/static/images/products/Coevals.jpg')
        self.assertContains(response, 'Burgundy')
        self.assertContains(response, 'id="colorSelect"')


class ReviewPermissionTests(TestCase):
    def setUp(self):
        self.category = create_category()
        self.product = create_product(self.category)
        self.user = create_active_user()
        self.review_data = {
            'subject': 'Great product',
            'review': 'Worked exactly as expected.',
            'rating': '4.5',
        }

    def create_paid_order_product(self, user=None, product=None):
        user = user or self.user
        product = product or self.product
        order = Order.objects.create(
            user=user,
            first_name='Review',
            last_name='Buyer',
            email=user.email,
            phone='07123456789',
            address_line_1='1 Review Street',
            county='London',
            postcode='RV1 1AA',
            order_total=Decimal('199.99'),
            tax=Decimal('40.00'),
            delivery_total=Decimal('0.00'),
            grand_total=Decimal('239.99'),
            is_ordered=True,
        )
        return OrderProduct.objects.create(
            order=order,
            user=user,
            product=product,
            quantity=1,
            product_price=product.price,
            ordered=True,
        )

    def post_review(self, hx_request=True):
        headers = {'HTTP_HX_REQUEST': 'true'} if hx_request else {}
        return self.client.post(
            reverse('submit_review', kwargs={'product_id': self.product.id}),
            self.review_data,
            HTTP_REFERER=reverse(
                'product_detail',
                kwargs={
                    'category_slug': self.category.slug,
                    'product_slug': self.product.slug,
                },
            ),
            **headers,
        )

    def test_anonymous_user_cannot_submit_review(self):
        response = self.post_review()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please sign in to leave a review.')
        self.assertFalse(ReviewRating.objects.exists())

    def test_authenticated_non_purchaser_cannot_submit_review(self):
        self.client.force_login(self.user)

        response = self.post_review()

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'You must purchase this product before reviewing it.',
        )
        self.assertFalse(ReviewRating.objects.exists())

    def test_verified_purchaser_can_submit_review(self):
        self.create_paid_order_product()
        self.client.force_login(self.user)

        response = self.post_review()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank you! Your review has been submitted.')
        review = ReviewRating.objects.get(user=self.user, product=self.product)
        self.assertEqual(review.subject, self.review_data['subject'])
        self.assertEqual(review.rating, 4.5)

    def test_existing_reviewer_can_update_review_without_new_purchase_check(self):
        ReviewRating.objects.create(
            user=self.user,
            product=self.product,
            subject='Original title',
            review='Original review',
            rating=3,
        )
        self.client.force_login(self.user)

        response = self.post_review()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank you! Your review has been updated.')
        review = ReviewRating.objects.get(user=self.user, product=self.product)
        self.assertEqual(review.subject, self.review_data['subject'])
        self.assertEqual(review.review, self.review_data['review'])
        self.assertEqual(review.rating, 4.5)
