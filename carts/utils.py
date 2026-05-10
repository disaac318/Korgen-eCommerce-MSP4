from .models import CartItem


def get_cart_id(request):
    cart_id = request.session.get('cart_id')
    if cart_id:
        return cart_id

    if not request.session.session_key:
        request.session.create()

    cart_id = request.session.session_key
    request.session['cart_id'] = cart_id
    return cart_id


def assign_session_cart_to_user(request):
    cart_id = request.session.get('cart_id')
    if not cart_id or not request.user.is_authenticated:
        return

    session_items = CartItem.objects.filter(
        cart__cart_id=cart_id,
        user__isnull=True,
        is_active=True,
    ).prefetch_related('variations')

    for session_item in session_items:
        session_variation_ids = sorted(
            session_item.variations.values_list('id', flat=True)
        )
        user_items = CartItem.objects.filter(
            user=request.user,
            product=session_item.product,
            is_active=True,
        ).prefetch_related('variations')

        matching_user_item = None
        for user_item in user_items:
            user_variation_ids = sorted(
                user_item.variations.values_list('id', flat=True)
            )
            if user_variation_ids == session_variation_ids:
                matching_user_item = user_item
                break

        if matching_user_item:
            matching_user_item.quantity += session_item.quantity
            matching_user_item.save(update_fields=['quantity'])
            session_item.delete()
        else:
            session_item.user = request.user
            session_item.save(update_fields=['user'])
