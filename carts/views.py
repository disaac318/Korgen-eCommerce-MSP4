from django.shortcuts import get_object_or_404, redirect, render
from carts.models import Cart, CartItem
from store.models import Product, Variation

# Create your views here.
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_variations = []

    if request.method == 'POST':
        for variation_category, variation_value in request.POST.items():
            if variation_category == 'csrfmiddlewaretoken' or not variation_value:
                continue

            variation = Variation.objects.filter(
                product=product,
                variation_category__iexact=variation_category,
                variation_value__iexact=variation_value,
                is_active=True,
            ).first()

            if variation:
                product_variations.append(variation)
    elif product.variation_set.filter(is_active=True).exists():
        return redirect(
            'product_detail',
            category_slug=product.category.slug,
            product_slug=product.slug,
        )

    cart, _ = Cart.objects.get_or_create(cart_id=_cart_id(request))

    cart_items = CartItem.objects.filter(product=product, cart=cart).prefetch_related('variations')
    product_variation_ids = sorted(variation.id for variation in product_variations)

    for cart_item in cart_items:
        cart_item_variation_ids = sorted(
            cart_item.variations.values_list('id', flat=True)
        )

        if cart_item_variation_ids == product_variation_ids:
            cart_item.quantity += 1
            cart_item.save()
            break
    else:
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )
        if product_variations:
            cart_item.variations.add(*product_variations)

    return redirect('cart')


def increment_cart_item(request, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart')


def remove_from_cart(request, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('cart')


def delete_cart_item(request, cart_item_id):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
        cart_item.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += cart_item.sub_total()
            quantity += cart_item.quantity

        tax = total * 20 / 100
        grand_total = total + tax
    except Cart.DoesNotExist:
        cart_items = []

    context = {
        'total': total,
        'tax': tax,
        'grand_total': grand_total,
        'quantity': quantity,
        'cart_items': cart_items,
    }
    return render(request, 'carts/cart.html', context)
