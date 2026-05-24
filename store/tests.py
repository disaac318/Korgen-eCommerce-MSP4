from django.test import TestCase
from django.urls import reverse

from category.models import Category

from .models import Product


class SearchViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='Electronics',
            slug='electronics',
        )
        self.name_match = Product.objects.create(
            product_name='Action Camera',
            slug='action-camera',
            description='Compact travel video camera.',
            price='199.99',
            images='photos/products/action-camera.jpg',
            stock=5,
            is_available=True,
            category=self.category,
        )
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
