from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render

from carts.models import Cart

from .forms import RegistrationForm


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('accounts:login')

        messages.error(request, 'Please correct the errors below and try again.', extra_tags='danger')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, 'You have logged in successfully.')
            return redirect('home')

        messages.error(request, 'Invalid email or password. Please try again.', extra_tags='danger')

    return render(request, 'accounts/login.html')


def logout(request):
    if request.method == 'POST':
        cart_id = request.session.session_key
        if cart_id:
            Cart.objects.filter(cart_id=cart_id).delete()

        auth_logout(request)
        messages.success(request, 'You have logged out successfully.')
        return redirect('home')

    return render(request, 'accounts/logout.html')
