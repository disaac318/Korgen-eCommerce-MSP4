from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from carts.models import Cart, CartItem
from carts.utils import assign_session_cart_to_user, get_cart_id
from store.models import Product, Variation


def _get_selected_variations(request, product):
    selected_variations = []
    ignored_fields = {'csrfmiddlewaretoken', 'confirm'}

    for variation_category, variation_value in request.POST.items():
        if variation_category in ignored_fields or not variation_value:
            continue

        variation = Variation.objects.filter(
            product=product,
            variation_category__iexact=variation_category,
            variation_value__iexact=variation_value,
            is_active=True,
        ).first()

        if variation:
            selected_variations.append(variation)

    return selected_variations


def _get_matching_cart_item(cart_items, selected_variations):
    selected_variation_ids = sorted(
        variation.id for variation in selected_variations
    )

    for cart_item in cart_items:
        cart_item_variation_ids = sorted(
            cart_item.variations.values_list('id', flat=True)
        )

        if cart_item_variation_ids == selected_variation_ids:
            return cart_item

    return None


@login_required(login_url='accounts:login')
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_variations = []

    if request.method == 'POST':
        product_variations = _get_selected_variations(request, product)
    elif product.variation_set.filter(is_active=True).exists():
        return redirect(
            'product_detail',
            category_slug=product.category.slug,
            product_slug=product.slug,
        )

    cart, _ = Cart.objects.get_or_create(cart_id=get_cart_id(request))
    assign_session_cart_to_user(request)

    cart_items = CartItem.objects.filter(
        product=product,
        user=request.user,
        is_active=True,
    ).prefetch_related('variations')
    cart_item = _get_matching_cart_item(cart_items, product_variations)

    if cart_item and request.POST.get('confirm') != 'yes':
        context = {
            'cart_item': cart_item,
            'product': product,
            'product_variations': product_variations,
        }
        return render(request, 'carts/confirm_add.html', context)

    if cart_item:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(
            user=request.user,
            product=product,
            quantity=1,
            cart=cart,
        )
        if product_variations:
            cart_item.variations.add(*product_variations)

    return redirect('cart')


@login_required(login_url='accounts:login')
def increment_cart_item(request, cart_item_id):
    assign_session_cart_to_user(request)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        user=request.user,
        is_active=True,
    )
    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart')


@login_required(login_url='accounts:login')
def confirm_remove_from_cart(request, cart_item_id):
    assign_session_cart_to_user(request)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        user=request.user,
        is_active=True,
    )

    context = {
        'cart_item': cart_item,
        'action_type': 'decrease',
    }
    return render(request, 'carts/confirm_remove.html', context)


@login_required(login_url='accounts:login')
def confirm_delete_cart_item(request, cart_item_id):
    assign_session_cart_to_user(request)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        user=request.user,
        is_active=True,
    )

    context = {
        'cart_item': cart_item,
        'action_type': 'delete',
    }
    return render(request, 'carts/confirm_remove.html', context)


@login_required(login_url='accounts:login')
def remove_from_cart(request, cart_item_id):
    if request.method != 'POST':
        return redirect('cart')

    assign_session_cart_to_user(request)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        user=request.user,
        is_active=True,
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('cart')


@login_required(login_url='accounts:login')
def delete_cart_item(request, cart_item_id):
    if request.method != 'POST':
        return redirect('cart')

    assign_session_cart_to_user(request)
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        user=request.user,
        is_active=True,
    )
    cart_item.delete()

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0

    if not request.user.is_authenticated:
        context = {
            'total': total,
            'tax': tax,
            'grand_total': grand_total,
            'quantity': quantity,
            'cart_items': [],
        }
        return render(request, 'carts/cart.html', context)

    assign_session_cart_to_user(request)
    cart_items = CartItem.objects.filter(
        user=request.user,
        is_active=True,
    ).prefetch_related('variations')
    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity

    tax = total * 20 / 100
    grand_total = total + tax

    context = {
        'total': total,
        'tax': tax,
        'grand_total': grand_total,
        'quantity': quantity,
        'cart_items': cart_items,
    }
    return render(request, 'carts/cart.html', context)
