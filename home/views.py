from django.shortcuts import render
from store.models import Product

# Create your views here.
def index(request):
    products = Product.objects.filter(is_available=True)
    context = {
          'products': products,
     }
    return render(request, 'home/index.html', context)
