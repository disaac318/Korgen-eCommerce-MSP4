from django.shortcuts import render
from .models import Product


# Create your views here.
def store(request):
    products = Product.objects.filter(is_available=True)
    product_count = products.count()
    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
    }

    return render(request, 'store/store.html', context)
