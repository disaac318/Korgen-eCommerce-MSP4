from django.contrib import messages
from django.shortcuts import redirect, render

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
    return render(request, 'accounts/login.html')


def logout(request):
    return render(request, 'accounts/logout.html')
