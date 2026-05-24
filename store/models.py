from pathlib import PurePosixPath

from django.db import models
from django.db.models import Avg, Count
from django.db.models.functions import Lower
from django.templatetags.static import static

from category.models import Category

# Create your models here.
class Product(models.Model):
    PACKAGED_IMAGE_FILES = {
        'Action5-camera.jpg': 'Action5-camera.jpg',
        'Coevals.jpg': 'Coevals.jpg',
        'Coevals_JHte0VL.jpg': 'Coevals.jpg',
        'Hitmars-Shoes.jpg': 'Hitmars-Shoes.jpg',
        'Japanese_Cherry_Blossom_.jpeg': 'Japanese Cherry Blossom .jpeg',
        'Jetsetter-luggage.jpg': 'Jetsetter-luggage.jpg',
        'Nintendo_2.jpg': 'Nintendo 2.jpg',
        'Warm-Jacket.jpg': 'Warm-Jacket.jpg',
        'Winter-Jacket.jpg': 'Winter-Jacket.jpg',
        'Yellow-bag.png': 'Yellow-bag.png',
        'red-bag.png': 'red-bag.png',
    }

    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey('category.Category', on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.product_name

    @property
    def display_image_url(self):
        if not self.images:
            return ''

        image_file = PurePosixPath(self.images.name).name
        packaged_image_file = self.PACKAGED_IMAGE_FILES.get(image_file)
        if packaged_image_file:
            return static(f'images/products/{packaged_image_file}')

        return self.images.url

    def averageReview(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg('rating'))
        average = reviews['average']
        if average is None:
            return 0
        return round(average, 1)
    

    def countReview(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(count=Count('id'))
        return reviews['count'] or 0


class VariationManager(models.Manager):
    def colors(self):
        return super().filter(variation_category='color', is_active=True)

    def sizes(self):
        return super().filter(variation_category='size', is_active=True)


variation_category_choice = (
    ('color', 'color'),
    ('size', 'size'),
)

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=100, choices=variation_category_choice)
    variation_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    objects = VariationManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                'product',
                'variation_category',
                Lower('variation_value'),
                name='unique_product_variation_value_ci',
                violation_error_message='The selected variation has been chosen.',
            ),
        ]

    def __str__(self):
        return self.variation_value


class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject
