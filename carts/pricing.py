from decimal import Decimal

from django.conf import settings


VAT_RATE = Decimal('0.20')


def _money(value):
    """Normalize money values to two decimal places for consistent totals."""
    return Decimal(str(value)).quantize(Decimal('0.01'))


def calculate_delivery_total(order_total):
    """Return the delivery charge after applying the free-delivery threshold."""
    order_total = _money(order_total)
    free_threshold = _money(settings.DELIVERY_FREE_THRESHOLD)

    if order_total >= free_threshold:
        return Decimal('0.00')

    return _money(settings.DELIVERY_FLAT_RATE)


def calculate_cart_totals(cart_items):
    """Calculate subtotal, VAT, delivery, grand total, and item count."""
    total = Decimal('0.00')
    quantity = 0

    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity

    total = _money(total)
    tax = _money(total * VAT_RATE)
    delivery_total = calculate_delivery_total(total) if total else Decimal('0.00')
    grand_total = _money(total + tax + delivery_total)
    free_delivery_threshold = _money(settings.DELIVERY_FREE_THRESHOLD)

    return {
        'total': total,
        'tax': tax,
        'delivery_total': delivery_total,
        'free_delivery_threshold': free_delivery_threshold,
        'qualifies_for_free_delivery': (
            total >= free_delivery_threshold and total > Decimal('0.00')
        ),
        'grand_total': grand_total,
        'quantity': quantity,
    }
