from urllib.parse import urlencode

from django.contrib import messages
from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from carts.models import Cart

from .forms import RegistrationForm
from .models import Account
from .tokens import account_activation_token


@never_cache
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            activation_path = reverse(
                'accounts:activate',
                kwargs={'uidb64': uid, 'token': token},
            )
            activation_url = request.build_absolute_uri(activation_path)
            message = render_to_string('accounts/acc_verification_email.html', {
                'user': user,
                'activation_url': activation_url,
                'site_name': 'Korgen',
            })
            email = EmailMessage(
                'Activate your account.',
                message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.content_subtype = 'html'
            email.send()
            # messages.success(request, 'Registration successful. Please check your email to activate your account. If you do not see the email, check your spam or junk folder.', extra_tags='success')
            login_url = reverse('accounts:login')
            query = urlencode({
                'command': 'verification',
                'email': user.email,
            })
            return redirect(f'{login_url}?{query}')

        messages.error(request, 'Please correct the errors below and try again.', extra_tags='danger')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@never_cache
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, 'You have logged in successfully.')
            return redirect('accounts:dashboard')

        if Account.objects.filter(email__iexact=email, is_active=False).exists():
            messages.error(request, 'Please activate your account from the email we sent you.', extra_tags='danger')
        else:
            messages.error(request, 'Invalid email or password. Please try again.', extra_tags='danger')

    return render(request, 'accounts/login.html')


@login_required(login_url='accounts:login')
@require_POST
def logout(request):
    cart_id = request.session.session_key
    if cart_id:
        Cart.objects.filter(cart_id=cart_id).delete()

    auth_logout(request)
    messages.success(request, 'You have logged out successfully.')
    return redirect('home')


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is None or not account_activation_token.check_token(user, token):
        messages.error(request, 'Activation link is invalid or has expired.', extra_tags='danger')
        return redirect('accounts:login')

    if user.is_active:
        messages.info(request, 'Your account is already active. You can log in.')
        return redirect('accounts:login')

    user.is_active = True
    user.save(update_fields=['is_active'])
    messages.success(request, 'Your account has been activated successfully. You can now log in.')
    return redirect('accounts:login')


@login_required(login_url='accounts:login')
def dashboard(request):
    return render(request, 'accounts/dashboard.html')
