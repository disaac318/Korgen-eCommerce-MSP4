from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

from store.models import Product, ReviewRating

from .forms import ContactForm


def index(request):
    products = Product.objects.filter(is_available=True).order_by('created_date')

    # Get the reviews
    reviews = None
    for product in products:
        reviews = ReviewRating.objects.filter(product=product, status=True)

    context = {
        'products': products,
        'reviews': reviews,
    }

    return render(request, 'home/index.html', context)


def contact(request):
    form = ContactForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        contact_email = getattr(
            settings,
            'CONTACT_EMAIL',
            settings.DEFAULT_FROM_EMAIL,
        )
        cleaned_data = form.cleaned_data
        email = EmailMessage(
            subject=f"Korgen contact: {cleaned_data['subject']}",
            body=(
                f"Name: {cleaned_data['name']}\n"
                f"Email: {cleaned_data['email']}\n\n"
                f"{cleaned_data['message']}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_email],
            reply_to=[cleaned_data['email']],
        )
        email.send()
        messages.success(
            request,
            'Thanks for contacting us. We will get back to you soon.',
        )
        return redirect('contact')

    return render(request, 'home/contact.html', {'form': form})
