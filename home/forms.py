from django import forms


class ContactForm(forms.Form):
    """Customer enquiry form used by the contact page."""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Your name',
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'you@example.com',
            }
        ),
    )
    subject = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'How can we help?',
            }
        ),
    )
    message = forms.CharField(
        min_length=10,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'placeholder': 'Tell us what you need help with',
                'rows': 6,
            }
        ),
    )
