from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Order


@login_required(login_url='accounts:login')
def order_complete(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variations'),
        order_number=order_number,
        user=request.user,
    )
    return render(request, 'orders/order_complete.html', {'order': order})
