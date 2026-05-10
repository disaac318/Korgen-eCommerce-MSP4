from .models import CartItem
from .utils import assign_session_cart_to_user, get_cart_id


def cart_counter(request):
    cart_count = 0

    if request.user.is_authenticated:
        assign_session_cart_to_user(request)
        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    else:
        cart_id = request.session.get('cart_id')
        if not cart_id:
            return {'cart_count': cart_count}
        cart_items = CartItem.objects.filter(
            cart__cart_id=get_cart_id(request),
            user__isnull=True,
            is_active=True,
        )

    for cart_item in cart_items:
        cart_count += cart_item.quantity

    return {'cart_count': cart_count}
