from django import forms


class CheckoutForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    address_line_1 = forms.CharField(max_length=100)
    address_line_2 = forms.CharField(max_length=100, required=False)
    county = forms.CharField(max_length=50)
    postcode = forms.CharField(max_length=20)
    order_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    def __init__(self, *args, **kwargs):
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
            'order_notes': 'Order notes',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = placeholders[field_name]
