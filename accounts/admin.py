from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import Account, BillingDetails, UserProfile


class AccountAdmin(UserAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'username', 'phone_number',
        'date_joined', 'last_login', 'is_admin',
        'is_active', 'is_staff', 'is_superuser'
    )

    list_display_links = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

#     search_fields = ('email', 'username')
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


class UserProfileAdmin(admin.ModelAdmin):
    list_select_related = ('user',)

    def thumbnail(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 50%;">',
                obj.profile_picture.url,
            )
        return 'No Image'

    thumbnail.short_description = 'Profile Picture'
    list_display = ('thumbnail', 'user', 'address_line_1', 'address_line_2', 'city', 'county', 'postcode', 'country')
    search_fields = ('user__email', 'user__username')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and 'user' in form.base_fields:
            form.base_fields['user'].queryset = Account.objects.filter(userprofile__isnull=True)
        return form

    class Media:
        css = {
            'all': ('css/admin.css',)
        }


admin.site.register(Account, AccountAdmin)
admin.site.register(BillingDetails)
admin.site.register(UserProfile, UserProfileAdmin)
