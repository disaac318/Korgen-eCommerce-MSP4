from django.shortcuts import get_object_or_404, render
from category.models import Category
from carts.views import _cart_id
from .models import Product
from carts.models import CartItem


# Create your views here.
def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True)

    if category_slug is not None:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    product_count = products.count()
    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
    }

    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    single_product = get_object_or_404(
        Product,
        category__slug=category_slug,
        slug=product_slug,
        is_available=True,
    )
    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request),
        product=single_product,
    ).exists()

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
    }

    return render(request, 'store/product_detail.html', context)
