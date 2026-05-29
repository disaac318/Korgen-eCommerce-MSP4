from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator

from store.models import Product, Variation

# Create your models here.
class Cart(models.Model):
    """Anonymous shopping cart identified by the user's session id."""

    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    """Product line in either an anonymous cart or authenticated user's cart."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name='cartitem_quantity_at_least_one',
            ),
        ]

    def sub_total(self):
        """Return the line subtotal for cart and checkout totals."""
        return self.product.price * self.quantity

    def __str__(self):
        return self.product.product_name
