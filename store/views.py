from django.shortcuts import get_object_or_404, render

from category.models import Category

from .models import Product


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
