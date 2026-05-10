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
]
