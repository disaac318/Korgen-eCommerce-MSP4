from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Account, UserProfile


class RegistrationForm(forms.ModelForm):
    """Registration form that confirms and validates the submitted password."""

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter password',
            'class': 'form-control',
            'autocomplete': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
            'class': 'form-control',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'email', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'family-name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'username',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'autocomplete': 'email',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'first_name': 'Enter first name',
            'last_name': 'Enter last name',
            'username': 'Enter username',
            'phone_number': 'Enter phone number',
            'email': 'Enter email address',
        }

        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs['placeholder'] = placeholder

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        """Validate password confirmation and Django password-strength rules."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')

        if password:
            user = Account(
                first_name=cleaned_data.get('first_name', ''),
                last_name=cleaned_data.get('last_name', ''),
                username=cleaned_data.get('username', ''),
                email=cleaned_data.get('email', ''),
            )
            try:
                validate_password(password, user)
            except forms.ValidationError as error:
                self.add_error('password', error)

        return cleaned_data

    def save(self, commit=True):
        """Store a hashed password and leave activation to the email workflow."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = False

        if commit:
            user.save()

        return user
    
class UserForm(forms.ModelForm):
    """Editable account fields shown on the profile page."""

    class Meta:
        model = Account
        fields = ('first_name', 'last_name', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class UserProfileForm(forms.ModelForm):
    """Profile address and image upload form for authenticated users."""

    profile_picture = forms.ImageField(required=False, error_messages={'invalid': 'Image files only'}, widget=forms.FileInput)
    class Meta:
        model = UserProfile
        fields = (
            'address_line_1',
            'address_line_2',
            'city',
            'county',
            'postcode',
            'country',
            'profile_picture',
        )

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
