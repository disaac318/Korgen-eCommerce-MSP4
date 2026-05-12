from django.contrib import admin

from .models import Order, OrderProduct, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_id',
        'user',
        'payment_method',
        'amount_paid',
        'status',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('payment_id', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    readonly_fields = ('product', 'quantity', 'product_price', 'ordered')
    filter_horizontal = ('variations',)
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'payment',
        'full_name',
        'email',
        'delivery_total',
        'grand_total',
        'status',
        'is_ordered',
        'created_at',
    )
    list_filter = ('status', 'is_ordered', 'created_at')
    search_fields = ('order_number', 'payment__payment_id', 'first_name', 'last_name', 'email')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = (OrderProductInline,)


@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'product_price', 'ordered')
    list_filter = ('ordered', 'created_at')
    search_fields = ('order__order_number', 'product__product_name')
    filter_horizontal = ('variations',)
