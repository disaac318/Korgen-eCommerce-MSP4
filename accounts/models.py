from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class MyAccountManager(BaseUserManager):
    """Factory methods for the custom email-based account model."""

    def create_user(self, first_name, last_name, email, username, password=None):
        """Create a regular user with normalized email and hashed password."""
        if not email:
            raise ValueError('User must have an email address')
        if not username:
            raise ValueError('User must have a username')

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, username, password):
        """Create an administrator account with all staff flags enabled."""
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=password,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_active = True
        user.is_superadmin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, PermissionsMixin):
    """Custom user model that authenticates with email instead of username."""

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)

    objects = MyAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def full_name(self):
        """Return the display name used in templates and account pages."""
        return f'{self.first_name} {self.last_name}'

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True


class BillingDetails(models.Model):
    """Reusable billing address saved from checkout for future orders."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='billing_details',
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=50)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=50, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Billing details'
        verbose_name_plural = 'Billing details'

    @classmethod
    def fields_to_save(cls):
        """List fields shared between saved billing details and order forms."""
        return (
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_line_1',
            'address_line_2',
            'county',
            'postcode',
            'country',
        )

    def as_order_initial(self):
        """Convert saved billing details into initial data for checkout."""
        return {
            field_name: getattr(self, field_name)
            for field_name in self.fields_to_save()
        }

    @classmethod
    def from_order_cleaned_data(cls, cleaned_data):
        """Extract billing fields from validated order form data."""
        return {
            field_name: cleaned_data.get(field_name, '')
            for field_name in cls.fields_to_save()
        }

    def __str__(self):
        return f'Billing details for {self.user}'


class UserProfile(models.Model):
    """Additional account profile details that are separate from login data."""

    user = models.OneToOneField(Account, on_delete=models.CASCADE)
    address_line_1 = models.CharField(max_length=100, blank=True)
    address_line_2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50, blank=True)
    county = models.CharField(max_length=50, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=50, blank=True)
    profile_picture = models.ImageField(upload_to='userprofile', blank=True)

    def __str__(self):
        return self.user.first_name

    def full_address(self):
        """Return a comma-separated address without empty components."""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.county,
            self.postcode,
            self.country,
        ]
        return ', '.join(part for part in address_parts if part)
