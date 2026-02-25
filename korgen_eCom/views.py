from django.shortcuts import render

def home(request):
     return render(request, 'home.html')

def cart_view(request):
    return render(request, 'cart/cart.html')  # or 'cart.html' depending on your structur
