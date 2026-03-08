from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account


class AccountAdmin(UserAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'username',
        'date_joined', 'last_login', 'is_admin',
        'is_active', 'is_staff', 'is_superuser'
    )

#     list_display_links = ('email', 'first_name', 'last_name')
#     ordering = ('-date_joined',)

#     search_fields = ('email', 'username')
    readonly_fields = ('date_joined', 'last_login')


admin.site.register(Account, AccountAdmin)
