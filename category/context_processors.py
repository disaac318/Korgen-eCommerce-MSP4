from .models import Category


def menu_links(request):
    categories = Category.objects.order_by('category_name')
    return {
        'categories': categories,
    }
