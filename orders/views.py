import base64
import json
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from carts.models import CartItem

from .models import Order, Payment


def _paypal_credentials_are_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


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


def _get_pending_order(request, order_number):
    return get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variations'),
        order_number=order_number,
        user=request.user,
        is_ordered=False,
    )


@login_required(login_url='accounts:login')
def order_complete(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variations'),
        order_number=order_number,
        user=request.user,
    )
    return render(request, 'orders/order_complete.html', {'order': order})


@login_required(login_url='accounts:login')
def payment(request, order_number):
    order = _get_pending_order(request, order_number)
    context = {
        'order': order,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_currency': settings.PAYPAL_CURRENCY,
    }
    return render(request, 'orders/payment.html', context)


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

    try:
        access_token = _get_paypal_access_token()
        paypal_order = _paypal_request(
            '/v2/checkout/orders',
            payload,
            access_token,
        )
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as error:
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

    if not capture_id:
        return _paypal_json_response('PayPal capture response was invalid.')

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        payment, _ = Payment.objects.update_or_create(
            payment_id=capture_id,
            defaults={
                'user': request.user,
                'payment_method': 'PayPal',
                'amount_paid': Decimal(str(order.grand_total)),
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
        else:
            return JsonResponse({
                'error': 'PayPal payment was not completed.',
                'status': payment.status,
            }, status=400)

    return JsonResponse({
        'status': payment.status,
        'redirect_url': reverse(
            'orders:order_complete',
            kwargs={'order_number': order.order_number},
        ),
    })
