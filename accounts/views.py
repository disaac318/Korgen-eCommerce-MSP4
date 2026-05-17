import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    url_has_allowed_host_and_scheme,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from carts.utils import assign_session_cart_to_user

from .forms import RegistrationForm, UserProfileForm, UserForm
from .models import Account, UserProfile
from .tokens import account_activation_token
from orders.models import Order



logger = logging.getLogger(__name__)


def _send_multipart_email(subject, template_base, context, recipient):
    text_message = render_to_string(f'{template_base}.txt', context)
    html_message = render_to_string(f'{template_base}.html', context)
    email = EmailMultiAlternatives(
        subject,
        text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send()


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
            email_context = {
                'user': user,
                'activation_url': activation_url,
                'site_name': 'Korgen',
            }

            try:
                _send_multipart_email(
                    'Activate your account.',
                    'accounts/acc_verification_email',
                    email_context,
                    user.email,
                )
            except Exception:
                logger.exception('Failed to send activation email to %s', user.email)
                user.delete()
                form.add_error(
                    None,
                    'We could not send your activation email. Please try again later.',
                )
                return render(request, 'accounts/register.html', {'form': form})

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
            guest_cart_id = request.session.get('cart_id')
            auth_login(request, user)
            if request.POST.get('remember'):
                request.session.set_expiry(settings.REMEMBER_ME_SESSION_AGE)
            else:
                request.session.set_expiry(0)
            if guest_cart_id:
                request.session['cart_id'] = guest_cart_id
                assign_session_cart_to_user(request)
            messages.success(request, 'You have logged in successfully.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('accounts:dashboard')

        if Account.objects.filter(email__iexact=email, is_active=False).exists():
            messages.error(request, 'Please activate your account from the email we sent you.', extra_tags='danger')
        else:
            messages.error(request, 'Invalid email or password. Please try again.', extra_tags='danger')

    return render(request, 'accounts/login.html')


@login_required(login_url='accounts:login')
@require_POST
def logout(request):
    request.session.pop('cart_id', None)
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
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()
    context = {
        'orders_count': orders_count,
        'orders': orders,
    }
    return render(request, 'accounts/dashboard.html', context)


@never_cache
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = Account.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            reset_path = reverse('accounts:password_reset_confirm', kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            reset_url = request.build_absolute_uri(reset_path)
            email_context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Korgen',
            }
            try:
                _send_multipart_email(
                    'Password Reset Request',
                    'accounts/password_reset_email',
                    email_context,
                    user.email,
                )
            except Exception:
                logger.exception('Failed to send password reset email to %s', user.email)

        messages.success(
            request,
            'If an active account exists for that email address, a password reset link has been sent.',
            extra_tags='success',
        )
        return redirect('accounts:login')

    return render(request, 'accounts/password_reset.html')


@never_cache
def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'Password reset link is invalid or has expired.', extra_tags='danger')
        return redirect('accounts:password_reset')

    form = SetPasswordForm(user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your password has been reset successfully. You can now log in.')
        return redirect('accounts:login')

    return render(request, 'accounts/password_reset_confirm.html', {'form': form})


def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'accounts/my_orders.html', context)

@login_required(login_url='accounts:login')
def edit_profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:edit_profile')
        else:
            messages.error(request, 'Please correct the errors below and try again.', extra_tags='danger')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': user_profile,
        'userprofile': user_profile,
    }
    return render(request, 'accounts/edit_profile.html', context)
    
