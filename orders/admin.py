from django.contrib import admin

from .models import Order, OrderProduct


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
        'full_name',
        'email',
        'grand_total',
        'status',
        'is_ordered',
        'created_at',
    )
    list_filter = ('status', 'is_ordered', 'created_at')
    search_fields = ('order_number', 'first_name', 'last_name', 'email')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines = (OrderProductInline,)


@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'product_price', 'ordered')
    list_filter = ('ordered', 'created_at')
    search_fields = ('order__order_number', 'product__product_name')
    filter_horizontal = ('variations',)
