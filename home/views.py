from django.shortcuts import render

from store.models import Product, ReviewRating


def index(request):
    products = Product.objects.filter(is_available=True).order_by('created_date')

    # Get the reviews
    reviews = None
    for product in products:
        reviews = ReviewRating.objects.filter(product=product, status=True)

    context = {
        'products': products,
        'reviews': reviews,
    }

    return render(request, 'home/index.html', context)
