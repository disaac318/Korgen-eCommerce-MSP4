from django.conf import settings
from django.db import models
from django.utils import timezone

from store.models import Product, Variation


class Payment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    payment_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=100)
    paypal_order_id = models.CharField(max_length=100, blank=True)
    payer_email = models.EmailField(blank=True)
    payer_name = models.CharField(max_length=150, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    transaction_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.payment_id


class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_ACCEPTED = 'accepted'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = (
        (STATUS_NEW, 'New'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=50)
    postcode = models.CharField(max_length=20)
    order_notes = models.TextField(blank=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    ip = models.GenericIPAddressField(blank=True, null=True)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.order_number:
            self.order_number = f'{timezone.now():%Y%m%d}{self.pk}'
            super().save(update_fields=['order_number'])

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def full_address(self):
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.county,
            self.postcode,
        ]
        return ', '.join(part for part in address_parts if part)

    def __str__(self):
        return self.order_number


class OrderProduct(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variations = models.ManyToManyField(Variation, blank=True)
    quantity = models.PositiveIntegerField()
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sub_total(self):
        return self.product_price * self.quantity

    def __str__(self):
        if self.product:
            return self.product.product_name
        return f'Order item {self.pk}'
