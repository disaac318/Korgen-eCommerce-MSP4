from django.shortcuts import get_object_or_404, render
from category.models import Category
from .models import Product
from django.core.paginator import Paginator


# Create your views here.
def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True).order_by('id')
    selected_category = None

    if category_slug is not None:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    product_count = products.count()
    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
        'selected_category': selected_category,
    }

    paginator = Paginator(products, 8)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    page_range = paginator.get_elided_page_range(
        number=paged_products.number,
        on_each_side=1,
        on_ends=1,
    )

    context['products'] = paged_products
    context['page_range'] = page_range

    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    single_product = get_object_or_404(
        Product,
        category__slug=category_slug,
        slug=product_slug,
        is_available=True,
    )
    context = {
        'single_product': single_product,
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    products = None
    product_count = 0

    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.filter(
                is_available=True,
                product_name__icontains=keyword,
            ).order_by('id')

            products = Product.objects.order_by('-created_date').filter(description__icontains=keyword)
            
            product_count = products.count()

    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
    }

    return render(request, 'store/store.html', context)
