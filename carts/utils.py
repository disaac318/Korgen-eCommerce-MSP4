from .models import CartItem


def get_cart_id(request):
    cart_id = request.session.session_key
    if not cart_id:
        request.session.create()
        cart_id = request.session.session_key
    return cart_id


def assign_session_cart_to_user(request):
    cart_id = request.session.session_key
    if not cart_id or not request.user.is_authenticated:
        return

    CartItem.objects.filter(
        cart__cart_id=cart_id,
        user__isnull=True,
    ).update(user=request.user)
