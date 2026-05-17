from django.contrib import admin
from .models import Product, ReviewRating, Variation


# Register your models here.
class ProductAdmin(admin.ModelAdmin):
     prepopulated_fields = {'slug': ('product_name',)}
     list_display = ('product_name',   'price', 'stock', 'category', 'created_date', 'modified_date', 'is_available')


class VariationAdmin(admin.ModelAdmin):
     list_display = ('product', 'variation_category', 'variation_value', 'is_active')
     list_editable = ('is_active',)
     list_filter = ('product', 'variation_category', 'variation_value')


class ReviewRatingAdmin(admin.ModelAdmin):
     list_display = ('product', 'user', 'subject', 'rating', 'status', 'created_at')
     list_filter = ('product', 'status', 'created_at')


admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(ReviewRating, ReviewRatingAdmin)
