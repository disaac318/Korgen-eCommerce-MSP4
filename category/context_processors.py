from .models import Category


# def menu_links(request):
#     links = Category.objects.order_by('category_name')
#     return {
#         'links': links,
#     }


def menu_links(request):
    categories = Category.objects.all()
    return {
        'categories': categories,
    }
