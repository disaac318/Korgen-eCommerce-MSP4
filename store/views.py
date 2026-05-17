from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from category.models import Category
from .models import Product, ReviewRating
from django.core.paginator import Paginator
from .forms import ReviewForm
from orders.models import OrderProduct


# Create your views here.
def _user_has_purchased_product(user, product_id):
    if not user.is_authenticated:
        return False

    return OrderProduct.objects.filter(
        user=user,
        product_id=product_id,
        ordered=True,
        order__is_ordered=True,
    ).exists()


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

    reviews = ReviewRating.objects.filter(
        product_id=single_product.id,
        status=True,
    )

    color_variations = single_product.variation_set.colors()
    size_variations = single_product.variation_set.sizes()
    can_review = _user_has_purchased_product(request.user, single_product.id)
    review_purchase_message = request.session.pop('review_purchase_message', '')
    review_login_message = request.session.pop('review_login_message', '')
    

    context = {
        'single_product': single_product,
        'color_variations': color_variations,
        'size_variations': size_variations,
        'can_review': can_review,
        'review_purchase_message': review_purchase_message,
        'review_login_message': review_login_message,
        'reviews': reviews,
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


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER') or 'store'

    if request.method != 'POST':
        return redirect(url)

    if not request.user.is_authenticated:
        request.session['review_login_message'] = 'Please sign in to leave a review.'
        return redirect(url)

    review = ReviewRating.objects.filter(
        user=request.user,
        product_id=product_id,
    ).first()

    if review is None and not _user_has_purchased_product(request.user, product_id):
        request.session['review_purchase_message'] = 'You must purchase this product before reviewing it.'
        return redirect(url)

    if review is not None:
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            request.session.pop('review_purchase_message', None)
            request.session.pop('review_login_message', None)
            messages.success(request, 'Thank you! Your review has been updated.')
        else:
            messages.error(request, 'Please check your review and try again.')
    else:
        form = ReviewForm(request.POST)
        if form.is_valid():
            data = form.save(commit=False)
            data.ip = request.META.get('REMOTE_ADDR')
            data.product_id = product_id
            data.user = request.user
            data.save()
            request.session.pop('review_purchase_message', None)
            request.session.pop('review_login_message', None)
            messages.success(request, 'Thank you! Your review has been submitted.')
        else:
            messages.error(request, 'Please check your review and try again.')

    return redirect(url)
