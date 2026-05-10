from .models import CartItem
from .utils import assign_session_cart_to_user


def cart_counter(request):
    cart_count = 0

    if not request.user.is_authenticated:
        return {'cart_count': cart_count}

    assign_session_cart_to_user(request)
    cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    for cart_item in cart_items:
        cart_count += cart_item.quantity

    return {'cart_count': cart_count}
