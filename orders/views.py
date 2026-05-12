import base64
import json
import logging
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from carts.models import CartItem
from carts.pricing import calculate_delivery_total

from .models import Order, Payment


logger = logging.getLogger(__name__)


def _paypal_credentials_are_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def _stripe_credentials_are_configured():
    return bool(settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY)


def _stripe_live_payments_are_blocked():
    return (
        not settings.STRIPE_ALLOW_LIVE_PAYMENTS
        and (
            settings.STRIPE_PUBLIC_KEY.startswith('pk_live_')
            or settings.STRIPE_SECRET_KEY.startswith('sk_live_')
        )
    )


def _send_order_received_email(order, request=None):
    invoice_path = reverse(
        'orders:invoice',
        kwargs={'order_number': order.order_number},
    )
    invoice_url = (
        request.build_absolute_uri(invoice_path)
        if request
        else invoice_path
    )
    context = {
        'order': order,
        'invoice_url': invoice_url,
        'items': order.items.select_related('product').prefetch_related(
            'variations',
        ),
    }
    text_message = render_to_string(
        'orders/email/order_received.txt',
        context,
    )
    html_message = render_to_string(
        'orders/email/order_received.html',
        context,
    )
    email = EmailMultiAlternatives(
        f'Order received #{order.order_number}',
        text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send()


def _paypal_json_response(error_message, status=502, details=None):
    data = {'error': error_message}
    if settings.DEBUG and details:
        data['details'] = details
    return JsonResponse(data, status=status)


def _paypal_error_details(error):
    if isinstance(error, HTTPError):
        body = error.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body

    return str(error)


def _get_paypal_access_token():
    credentials = (
        f'{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}'
    ).encode()
    auth_header = base64.b64encode(credentials).decode()
    request = Request(
        f'{settings.PAYPAL_API_BASE}/v1/oauth2/token',
        data=urlencode({'grant_type': 'client_credentials'}).encode(),
        headers={
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )

    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode())
        return data['access_token']


def _paypal_request(path, payload, access_token):
    request = Request(
        f'{settings.PAYPAL_API_BASE}{path}',
        data=json.dumps(payload).encode(),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def _stripe_request(path, payload=None, method='POST'):
    encoded_credentials = base64.b64encode(
        f'{settings.STRIPE_SECRET_KEY}:'.encode(),
    ).decode()
    data = urlencode(payload or {}).encode() if payload is not None else None
    request = Request(
        f'{settings.STRIPE_API_BASE}{path}',
        data=data,
        headers={
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method=method,
    )

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def _stripe_amount_in_minor_units(amount):
    return int((Decimal(str(amount)) * Decimal('100')).quantize(Decimal('1')))


def _build_stripe_checkout_session_payload(order, success_url, cancel_url):
    return {
        'mode': 'payment',
        'client_reference_id': order.order_number,
        'customer_email': order.email,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'payment_method_types[0]': settings.STRIPE_PAYMENT_METHOD_TYPES[0],
        'line_items[0][quantity]': '1',
        'line_items[0][price_data][currency]': settings.STRIPE_CURRENCY,
        'line_items[0][price_data][unit_amount]': str(
            _stripe_amount_in_minor_units(order.grand_total),
        ),
        'line_items[0][price_data][product_data][name]': (
            f'Korgen order #{order.order_number}'
        ),
        'metadata[order_number]': order.order_number,
    }


def _mark_order_paid(order, payment):
    order.payment = payment
    order.status = Order.STATUS_ACCEPTED
    order.is_ordered = True
    order.save(update_fields=[
        'payment',
        'status',
        'is_ordered',
        'updated_at',
    ])
    order.items.update(ordered=True)
    CartItem.objects.filter(user=order.user, is_active=True).delete()


def _get_pending_order(request, order_number):
    return get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variations'),
        order_number=order_number,
        user=request.user,
        is_ordered=False,
    )


def _get_paid_order(request, order_number):
    return get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variations'),
        order_number=order_number,
        user=request.user,
        is_ordered=True,
    )


@login_required(login_url='accounts:login')
def order_complete(request, order_number):
    order = _get_paid_order(request, order_number)
    return render(request, 'orders/order_complete.html', {'order': order})


@login_required(login_url='accounts:login')
def invoice(request, order_number):
    order = _get_paid_order(request, order_number)
    return render(request, 'orders/invoice.html', {'order': order})


@login_required(login_url='accounts:login')
def invoice_pdf(request, order_number):
    order = _get_paid_order(request, order_number)
    html = render_to_string(
        'orders/invoice_pdf.html',
        {'order': order},
        request=request,
    )

    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        return HttpResponse(
            (
                'Invoice PDF generation is not available. '
                'Install WeasyPrint and its system dependencies.'
            ),
            status=503,
            content_type='text/plain',
        )

    pdf = HTML(
        string=html,
        base_url=request.build_absolute_uri('/'),
    ).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="invoice-{order.order_number}.pdf"'
    )
    return response


@login_required(login_url='accounts:login')
def payment(request, order_number):
    order = _get_pending_order(request, order_number)
    paypal_payment_cancelled = (
        request.GET.get('payment_status') == 'paypal_cancelled'
    )
    free_delivery_threshold = Decimal(str(settings.DELIVERY_FREE_THRESHOLD))
    context = {
        'order': order,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_currency': settings.PAYPAL_CURRENCY,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'paypal_payment_cancelled': paypal_payment_cancelled,
        'free_delivery_threshold': free_delivery_threshold,
        'qualifies_for_free_delivery': (
            order.delivery_total == calculate_delivery_total(order.order_total)
            and order.delivery_total == Decimal('0.00')
            and order.order_total >= free_delivery_threshold
        ),
    }
    return render(request, 'orders/payment.html', context)


@login_required(login_url='accounts:login')
@require_POST
def create_stripe_checkout_session(request, order_number):
    if not _stripe_credentials_are_configured():
        return JsonResponse({
            'error': 'Stripe credentials are not configured.',
        }, status=503)

    if _stripe_live_payments_are_blocked():
        return JsonResponse({
            'error': (
                'Stripe live payments are disabled for this test phase. '
                'Use Stripe test keys or enable live payments explicitly.'
            ),
        }, status=503)

    order = _get_pending_order(request, order_number)
    success_url = (
        request.build_absolute_uri(
            reverse(
                'orders:stripe_success',
                kwargs={'order_number': order.order_number},
            ),
        )
        + '?session_id={CHECKOUT_SESSION_ID}'
    )
    cancel_url = request.build_absolute_uri(
        reverse(
            'orders:stripe_cancel',
            kwargs={'order_number': order.order_number},
        ),
    )
    payload = _build_stripe_checkout_session_payload(
        order,
        success_url,
        cancel_url,
    )
    logger.info('Creating Stripe checkout session payload: %s', payload)

    try:
        session = _stripe_request('/v1/checkout/sessions', payload)
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
        logger.exception('Unable to create Stripe checkout session')
        return JsonResponse({
            'error': 'Unable to create Stripe checkout session.',
            'details': _paypal_error_details(error),
        }, status=502)

    return JsonResponse({
        'id': session['id'],
        'url': session['url'],
    })


@login_required(login_url='accounts:login')
def stripe_success(request, order_number):
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'Stripe session id was missing.')
        return redirect('orders:payment', order_number=order_number)

    order = _get_pending_order(request, order_number)

    try:
        session = _stripe_request(
            f'/v1/checkout/sessions/{session_id}',
            payload=None,
            method='GET',
        )
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
        logger.exception('Unable to retrieve Stripe checkout session')
        messages.error(request, 'Stripe payment could not be verified.')
        return redirect('orders:payment', order_number=order.order_number)

    if (
        session.get('payment_status') != 'paid'
        or session.get('client_reference_id') != order.order_number
    ):
        messages.error(request, 'Stripe payment was not completed.')
        return redirect('orders:payment', order_number=order.order_number)

    should_send_order_email = False
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        was_already_ordered = order.is_ordered
        payment_id = session.get('payment_intent') or session['id']
        payment, _ = Payment.objects.update_or_create(
            payment_id=payment_id,
            defaults={
                'user': request.user,
                'payment_method': 'Stripe',
                'amount_paid': Decimal(str(order.grand_total)),
                'payer_email': (
                    session.get('customer_details', {}).get('email')
                    or session.get('customer_email', '')
                ),
                'payer_name': session.get('customer_details', {}).get(
                    'name',
                    '',
                ),
                'currency': session.get(
                    'currency',
                    settings.STRIPE_CURRENCY,
                ).upper(),
                'transaction_data': session,
                'status': Payment.STATUS_COMPLETED,
            },
        )
        _mark_order_paid(order, payment)
        should_send_order_email = not was_already_ordered

    if should_send_order_email:
        try:
            _send_order_received_email(order, request)
        except Exception:
            logger.exception(
                'Failed to send order received email for order %s',
                order.order_number,
            )

    return redirect(
        'orders:order_complete',
        order_number=order.order_number,
    )


@login_required(login_url='accounts:login')
def stripe_cancel(request, order_number):
    messages.warning(request, 'Stripe checkout was cancelled.')
    return redirect('orders:payment', order_number=order_number)


@login_required(login_url='accounts:login')
def paypal_cancel(request, order_number):
    _get_pending_order(request, order_number)
    messages.warning(
        request,
        'The PayPal payment method was not completed.',
    )
    payment_url = reverse(
        'orders:payment',
        kwargs={'order_number': order_number},
    )
    return redirect(f'{payment_url}?payment_status=paypal_cancelled')


@login_required(login_url='accounts:login')
@require_POST
def create_paypal_order(request, order_number):
    if not _paypal_credentials_are_configured():
        return _paypal_json_response(
            'PayPal credentials are not configured.',
            status=503,
        )

    order = _get_pending_order(request, order_number)
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [
            {
                'reference_id': order.order_number,
                'amount': {
                    'currency_code': settings.PAYPAL_CURRENCY,
                    'value': f'{order.grand_total:.2f}',
                },
            },
        ],
    }
    logger.info('Creating PayPal order payload: %s', payload)

    try:
        access_token = _get_paypal_access_token()
        paypal_order = _paypal_request(
            '/v2/checkout/orders',
            payload,
            access_token,
        )
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
        logger.exception('Unable to create PayPal order')
        return _paypal_json_response(
            'Unable to create PayPal order.',
            details=_paypal_error_details(error),
        )

    return JsonResponse({'id': paypal_order['id']})


@login_required(login_url='accounts:login')
@require_POST
def capture_paypal_order(request, order_number):
    if not _paypal_credentials_are_configured():
        return _paypal_json_response(
            'PayPal credentials are not configured.',
            status=503,
        )

    order = _get_pending_order(request, order_number)

    try:
        request_data = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return _paypal_json_response('Invalid PayPal capture request.', 400)

    paypal_order_id = request_data.get('paypal_order_id')
    if not paypal_order_id:
        return _paypal_json_response('Missing PayPal order id.', 400)

    try:
        access_token = _get_paypal_access_token()
        paypal_order = _paypal_request(
            f'/v2/checkout/orders/{paypal_order_id}/capture',
            {},
            access_token,
        )
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
        logger.exception('Unable to capture PayPal order')
        return _paypal_json_response(
            'Unable to capture PayPal order.',
            details=_paypal_error_details(error),
        )

    captures = (
        paypal_order.get('purchase_units', [{}])[0]
        .get('payments', {})
        .get('captures', [])
    )
    capture = captures[0] if captures else {}
    capture_id = capture.get('id')
    capture_status = capture.get('status', '').lower()
    capture_amount = capture.get('amount', {})
    payer = paypal_order.get('payer', {})
    payer_name = payer.get('name', {})
    payer_full_name = ' '.join(
        part for part in [
            payer_name.get('given_name', ''),
            payer_name.get('surname', ''),
        ]
        if part
    )

    if not capture_id:
        return _paypal_json_response('PayPal capture response was invalid.')

    should_send_order_email = False
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        was_already_ordered = order.is_ordered
        payment, _ = Payment.objects.update_or_create(
            payment_id=capture_id,
            defaults={
                'user': request.user,
                'payment_method': 'PayPal',
                'amount_paid': Decimal(str(order.grand_total)),
                'paypal_order_id': paypal_order_id,
                'payer_email': payer.get('email_address', ''),
                'payer_name': payer_full_name,
                'currency': capture_amount.get(
                    'currency_code',
                    settings.PAYPAL_CURRENCY,
                ),
                'transaction_data': paypal_order,
                'status': (
                    Payment.STATUS_COMPLETED
                    if capture_status == Payment.STATUS_COMPLETED
                    else Payment.STATUS_FAILED
                ),
            },
        )

        if payment.status == Payment.STATUS_COMPLETED:
            order.payment = payment
            order.status = Order.STATUS_ACCEPTED
            order.is_ordered = True
            order.save(update_fields=[
                'payment',
                'status',
                'is_ordered',
                'updated_at',
            ])
            order.items.update(ordered=True)
            CartItem.objects.filter(user=request.user, is_active=True).delete()
            should_send_order_email = not was_already_ordered
        else:
            return JsonResponse({
                'error': 'PayPal payment was not completed.',
                'status': payment.status,
            }, status=400)

    if should_send_order_email:
        try:
            _send_order_received_email(order, request)
        except Exception:
            logger.exception(
                'Failed to send order received email for order %s',
                order.order_number,
            )

    return JsonResponse({
        'status': payment.status,
        'redirect_url': reverse(
            'orders:order_complete',
            kwargs={'order_number': order.order_number},
        ),
    })
