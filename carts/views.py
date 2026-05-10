from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from carts.forms import CheckoutForm
from carts.models import Cart, CartItem
from carts.utils import assign_session_cart_to_user, get_cart_id
from orders.models import Order, OrderProduct
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


def _cart_items_for_request(request):
    if request.user.is_authenticated:
        assign_session_cart_to_user(request)
        return CartItem.objects.filter(user=request.user, is_active=True)

    return CartItem.objects.filter(
        cart__cart_id=get_cart_id(request),
        user__isnull=True,
        is_active=True,
    )


def _get_cart_item_for_request(request, cart_item_id):
    return _cart_items_for_request(request).filter(id=cart_item_id).first()


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
    if request.user.is_authenticated:
        assign_session_cart_to_user(request)

    cart_items = _cart_items_for_request(request).filter(
        product=product,
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
            user=request.user if request.user.is_authenticated else None,
            product=product,
            quantity=1,
            cart=cart,
        )
        if product_variations:
            cart_item.variations.add(*product_variations)

    return redirect('cart')


def increment_cart_item(request, cart_item_id):
    cart_item = _get_cart_item_for_request(request, cart_item_id)
    if cart_item is None:
        messages.warning(request, 'That cart item is no longer available.')
        return redirect('cart')

    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart')


def confirm_remove_from_cart(request, cart_item_id):
    cart_item = _get_cart_item_for_request(request, cart_item_id)
    if cart_item is None:
        messages.warning(request, 'That cart item is no longer available.')
        return redirect('cart')

    context = {
        'cart_item': cart_item,
        'action_type': 'decrease',
    }
    return render(request, 'carts/confirm_remove.html', context)


def confirm_delete_cart_item(request, cart_item_id):
    cart_item = _get_cart_item_for_request(request, cart_item_id)
    if cart_item is None:
        messages.warning(request, 'That cart item is no longer available.')
        return redirect('cart')

    context = {
        'cart_item': cart_item,
        'action_type': 'delete',
    }
    return render(request, 'carts/confirm_remove.html', context)


def remove_from_cart(request, cart_item_id):
    if request.method != 'POST':
        return redirect('cart')

    cart_item = _get_cart_item_for_request(request, cart_item_id)
    if cart_item is None:
        messages.warning(request, 'That cart item is no longer available.')
        return redirect('cart')

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('cart')


def delete_cart_item(request, cart_item_id):
    if request.method != 'POST':
        return redirect('cart')

    cart_item = _get_cart_item_for_request(request, cart_item_id)
    if cart_item is None:
        messages.warning(request, 'That cart item is no longer available.')
        return redirect('cart')

    cart_item.delete()

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0

    cart_items = _cart_items_for_request(request).prefetch_related('variations')
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


@login_required(login_url='accounts:login')
def checkout(request):
    total = 0
    quantity = 0

    assign_session_cart_to_user(request)
    cart_items = CartItem.objects.filter(
        user=request.user,
        is_active=True,
    ).prefetch_related('variations')

    if not cart_items.exists():
        return redirect('cart')

    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity

    tax = total * Decimal('0.20')
    grand_total = total + tax
    initial = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    }
    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address_line_1=form.cleaned_data['address_line_1'],
                address_line_2=form.cleaned_data['address_line_2'],
                county=form.cleaned_data['county'],
                postcode=form.cleaned_data['postcode'],
                order_notes=form.cleaned_data['order_notes'],
                order_total=total,
                tax=tax,
                grand_total=grand_total,
                ip=request.META.get('REMOTE_ADDR'),
                is_ordered=True,
            )

            for cart_item in cart_items:
                order_product = OrderProduct.objects.create(
                    order=order,
                    user=request.user,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    product_price=cart_item.product.price,
                    ordered=True,
                )
                variations = list(cart_item.variations.all())
                if variations:
                    order_product.variations.add(*variations)

            cart_items.delete()

        messages.success(
            request,
            'Your order has been placed successfully.',
        )
        return redirect('orders:order_complete', order_number=order.order_number)

    context = {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'tax': tax,
        'grand_total': grand_total,
        'quantity': quantity,
    }
    return render(request, 'store/checkout.html', context)
