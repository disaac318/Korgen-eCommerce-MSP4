from .models import Category


def menu_links(request):
    """Expose sorted categories to navigation menus across the site."""
    categories = Category.objects.order_by('category_name')
    return {
        'categories': categories,
    }
