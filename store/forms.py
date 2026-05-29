from django import forms

from .models import ReviewRating


class ReviewForm(forms.ModelForm):
    """Product review form used after purchase eligibility is checked."""

    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']
