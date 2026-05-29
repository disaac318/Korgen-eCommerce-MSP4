from django import forms

from store.models import ReviewRating

class ReviewForm(forms.ModelForm):
    """Legacy review form definition kept for template-adjacent imports."""

    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']
        
