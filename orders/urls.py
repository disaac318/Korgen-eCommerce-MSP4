from django.urls import path

from . import views


app_name = 'orders'

urlpatterns = [
    path(
        'complete/<str:order_number>/',
        views.order_complete,
        name='order_complete',
    ),
    path(
        'payment/<str:order_number>/',
        views.payment,
        name='payment',
    ),
    path(
        'payment/<str:order_number>/paypal/create/',
        views.create_paypal_order,
        name='create_paypal_order',
    ),
    path(
        'payment/<str:order_number>/paypal/capture/',
        views.capture_paypal_order,
        name='capture_paypal_order',
    ),
    path(
        'payment/<str:order_number>/paypal/cancel/',
        views.paypal_cancel,
        name='paypal_cancel',
    ),
    path(
        'payment/<str:order_number>/stripe/create/',
        views.create_stripe_checkout_session,
        name='create_stripe_checkout_session',
    ),
    path(
        'payment/<str:order_number>/stripe/success/',
        views.stripe_success,
        name='stripe_success',
    ),
    path(
        'payment/<str:order_number>/stripe/cancel/',
        views.stripe_cancel,
        name='stripe_cancel',
    ),
]
