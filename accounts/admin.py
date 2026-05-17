from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, BillingDetails


class AccountAdmin(UserAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'username', 'phone_number',
        'date_joined', 'last_login', 'is_admin',
        'is_active', 'is_staff', 'is_superuser'
    )

#     list_display_links = ('email', 'first_name', 'last_name')
#     ordering = ('-date_joined',)

#     search_fields = ('email', 'username')
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


admin.site.register(Account, AccountAdmin)
admin.site.register(BillingDetails)
