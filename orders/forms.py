from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    """Checkout form for collecting delivery and order-note details."""

    class Meta:
        model = Order
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_line_1',
            'address_line_2',
            'county',
            'postcode',
            'country',
            'order_notes',
        )
        widgets = {
            'order_notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        """Apply Bootstrap classes and placeholders to all checkout fields."""
        super().__init__(*args, **kwargs)

        placeholders = {
            'first_name': 'First name',
            'last_name': 'Last name',
            'email': 'Email',
            'phone': 'Phone number',
            'address_line_1': 'Address line 1',
            'address_line_2': 'Address line 2',
            'county': 'County',
            'postcode': 'Postcode',
            'country': 'Country',
            'order_notes': 'Order notes',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = placeholders[field_name]
