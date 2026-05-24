from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from category.models import Category
from orders.models import OrderProduct

from .forms import ReviewForm
from .models import Product, ReviewRating, Variation


# Create your views here.
def _parse_price_filter(value):
    if not value:
        return None

    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        return None

    if price < 0:
        return None

    return price


def _user_has_purchased_product(user, product_id):
    if not user.is_authenticated:
        return False

    return OrderProduct.objects.filter(
        user=user,
        product_id=product_id,
        ordered=True,
        order__is_ordered=True,
    ).exists()


def _review_form_error_message(form):
    if 'rating' in form.errors:
        return 'Please select a star rating before submitting your review.'

    error_messages = []
    for field_errors in form.errors.values():
        error_messages.extend(str(error) for error in field_errors)

    return ' '.join(error_messages) or 'Please check your review and try again.'


def _product_reviews_context(product, user, **messages):
    reviews = ReviewRating.objects.filter(
        product_id=product.id,
        status=True,
    ).select_related('user', 'user__userprofile')

    return {
        'single_product': product,
        'can_review': _user_has_purchased_product(user, product.id),
        'reviews': reviews,
        'review_form_values': {},
        'is_hx_request': False,
        **messages,
    }


def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True)
    selected_category = None

    if category_slug is not None:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    size_options = Variation.objects.filter(
        product__in=products,
        variation_category='size',
        is_active=True,
    ).order_by('variation_value').values_list(
        'variation_value',
        flat=True,
    ).distinct()

    selected_size = request.GET.get('size', '').strip()
    selected_min_price = request.GET.get('min_price', '').strip()
    selected_max_price = request.GET.get('max_price', '').strip()
    min_price = _parse_price_filter(selected_min_price)
    max_price = _parse_price_filter(selected_max_price)

    if selected_size:
        products = products.filter(
            variation__variation_category='size',
            variation__variation_value__iexact=selected_size,
            variation__is_active=True,
        ).distinct()

    if min_price is not None:
        products = products.filter(price__gte=min_price)

    if max_price is not None:
        products = products.filter(price__lte=max_price)

    products = products.order_by('id')
    product_count = products.count()
    query_params = request.GET.copy()
    query_params.pop('page', None)
    for key in list(query_params):
        if not query_params.get(key):
            query_params.pop(key, None)

    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
        'selected_category': selected_category,
        'size_options': size_options,
        'selected_size': selected_size,
        'selected_min_price': selected_min_price,
        'selected_max_price': selected_max_price,
        'filter_query': query_params.urlencode(),
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

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'store/includes/store_browser.html', context)

    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    single_product = get_object_or_404(
        Product,
        category__slug=category_slug,
        slug=product_slug,
        is_available=True,
    )

    color_variations = single_product.variation_set.colors()
    size_variations = single_product.variation_set.sizes()
    review_purchase_message = request.session.pop('review_purchase_message', '')
    review_login_message = request.session.pop('review_login_message', '')
    review_form_message = request.session.pop('review_form_message', '')
    

    context = {
        'single_product': single_product,
        'color_variations': color_variations,
        'size_variations': size_variations,
        **_product_reviews_context(
            single_product,
            request.user,
            review_purchase_message=review_purchase_message,
            review_login_message=review_login_message,
            review_form_message=review_form_message,
        ),
    }

    return render(request, 'store/product_detail.html', context)


def search(request):
    products = None
    product_count = 0

    if 'keyword' in request.GET:
        keyword = request.GET.get('keyword', '').strip()
        if keyword:
            products = Product.objects.filter(
                is_available=True,
            ).filter(
                Q(product_name__icontains=keyword)
                | Q(description__icontains=keyword)
            ).order_by('-created_date')
            product_count = products.count()

    context = {
        'products': products,
        'product_count_label': f"{product_count} item{'s' if product_count != 1 else ''} found.",
    }

    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER') or 'store'
    product = get_object_or_404(Product, id=product_id, is_available=True)

    def render_reviews_partial(**context):
        return render(
            request,
            'store/includes/product_reviews.html',
            _product_reviews_context(
                product,
                request.user,
                is_hx_request=True,
                **context,
            ),
        )

    if request.method != 'POST':
        return redirect(url)

    if not request.user.is_authenticated:
        if request.headers.get('HX-Request') == 'true':
            return render_reviews_partial(
                review_login_message='Please sign in to leave a review.',
                review_form_values=request.POST,
            )
        request.session['review_login_message'] = 'Please sign in to leave a review.'
        return redirect(url)

    review = ReviewRating.objects.filter(
        user=request.user,
        product_id=product_id,
    ).first()

    if review is None and not _user_has_purchased_product(request.user, product_id):
        if request.headers.get('HX-Request') == 'true':
            return render_reviews_partial(
                review_purchase_message='You must purchase this product before reviewing it.',
                review_form_values=request.POST,
            )
        request.session['review_purchase_message'] = 'You must purchase this product before reviewing it.'
        return redirect(url)

    if review is not None:
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            request.session.pop('review_purchase_message', None)
            request.session.pop('review_login_message', None)
            request.session.pop('review_form_message', None)
            if request.headers.get('HX-Request') == 'true':
                return render_reviews_partial(
                    review_success_message='Thank you! Your review has been updated.'
                )
            messages.success(request, 'Thank you! Your review has been updated.')
        else:
            if request.headers.get('HX-Request') == 'true':
                return render_reviews_partial(
                    review_form_message=_review_form_error_message(form),
                    review_form_values=request.POST,
                )
            request.session['review_form_message'] = _review_form_error_message(form)
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
            request.session.pop('review_form_message', None)
            if request.headers.get('HX-Request') == 'true':
                return render_reviews_partial(
                    review_success_message='Thank you! Your review has been submitted.'
                )
            messages.success(request, 'Thank you! Your review has been submitted.')
        else:
            if request.headers.get('HX-Request') == 'true':
                return render_reviews_partial(
                    review_form_message=_review_form_error_message(form),
                    review_form_values=request.POST,
                )
            request.session['review_form_message'] = _review_form_error_message(form)

    return redirect(url)
