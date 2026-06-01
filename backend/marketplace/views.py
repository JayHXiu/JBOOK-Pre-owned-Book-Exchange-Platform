from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.models import User
from analytics.models import BehaviorLog
from catalog.models import BookBase, Category
from marketplace.models import BrowseHistory, Collect, SellBook
from marketplace.services import (
    filter_sell_queryset,
    home_sections,
    price_bounds,
    record_browse,
)
from mlapp.services import get_recommendations, predict_price


def home_view(request):
    sections = home_sections()
    rec_books = []
    if request.session.get('user_id'):
        rec_books = get_recommendations(request.session['user_id'], limit=8)
    sections['rec_books'] = rec_books
    sections['carousel_slides'] = [
        {'title': 'JBOOK', 'text': 'Campus second-hand books platform'},
        {'title': 'Smart pricing', 'text': 'AI-assisted seller pricing'},
        {'title': 'Data dashboard', 'text': 'Interactive ECharts analytics'},
    ]
    return render(request, 'marketplace/home.html', sections)


def book_list_view(request):
    qs, keyword = filter_sell_queryset(request)
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page', 1))
    categories = Category.objects.select_related('parent').all()
    price_min, price_max = price_bounds()
    return render(request, 'marketplace/list.html', {
        'page': page,
        'categories': categories,
        'keyword': keyword,
        'filters': request.GET,
        'price_min': int(price_min),
        'price_max': int(price_max),
        'selected_qualities': request.GET.getlist('quality'),
    })


def book_detail_view(request, sell_id):
    sell = get_object_or_404(
        SellBook.objects.select_related('book', 'book__category', 'user'),
        sell_id=sell_id,
    )
    sell.view_count += 1
    sell.save(update_fields=['view_count'])
    user = getattr(request, 'custom_user', None)
    BehaviorLog.objects.create(
        user=user, sell=sell, action_type=BehaviorLog.ACTION_VIEW,
        stay_time=int(request.GET.get('stay', 0) or 0),
    )
    record_browse(user.user_id if user else None, sell)

    collected = bool(user and Collect.objects.filter(user=user, sell=sell).exists())
    uid = user.user_id if user else None
    guess_like = get_recommendations(uid, limit=6, exclude_sell_id=sell_id) if uid else []
    suggested = predict_price({
        'original_price': float(sell.book.original_price or 50),
        'pub_year': sell.book.pub_year or 2020,
        'cat_id': sell.book.category_id,
        'quality': sell.quality,
    })
    browse_history = []
    if user:
        browse_history = BrowseHistory.objects.filter(user=user).exclude(
            sell_id=sell_id
        ).select_related('sell', 'sell__book')[:6]

    return render(request, 'marketplace/detail.html', {
        'sell': sell,
        'collected': collected,
        'guess_like': guess_like,
        'suggested_price': suggested,
        'browse_history': browse_history,
    })


@require_http_methods(['GET', 'POST'])
def sell_create_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    categories = Category.objects.all()
    if request.method == 'POST':
        try:
            isbn = request.POST.get('isbn', '').strip()
            book_name = request.POST.get('book_name', '').strip()
            cat_id = int(request.POST['cat_id'])
            original_price = Decimal(request.POST.get('original_price') or '0')
            second_price = Decimal(request.POST['second_price'])
            quality = int(request.POST.get('quality', 3))
        except (KeyError, ValueError, InvalidOperation):
            messages.error(request, 'Invalid form data')
            return render(request, 'marketplace/sell_form.html', {'categories': categories})

        book = BookBase.objects.filter(isbn=isbn).first()
        if not book:
            book = BookBase.objects.create(
                isbn=isbn or f'CUSTOM-{request.session["user_id"]}-{SellBook.objects.count()}',
                book_name=book_name,
                author=request.POST.get('author', ''),
                publisher=request.POST.get('publisher', ''),
                pub_year=int(request.POST['pub_year']) if request.POST.get('pub_year') else None,
                original_price=original_price,
                category_id=cat_id,
                book_desc=request.POST.get('book_desc', ''),
            )

        cover = ''
        if request.FILES.get('cover_img'):
            from django.core.files.storage import default_storage
            f = request.FILES['cover_img']
            if f.size > 2 * 1024 * 1024:
                messages.error(request, 'Image max 2MB')
                return render(request, 'marketplace/sell_form.html', {'categories': categories})
            path = default_storage.save(f'covers/{f.name}', f)
            cover = default_storage.url(path)

        sell = SellBook.objects.create(
            book=book, user_id=request.session['user_id'],
            second_price=second_price, quality=quality, cover_img=cover, audit_status=0,
        )
        messages.success(request, 'Submitted for review')
        return redirect('book_detail', sell_id=sell.sell_id)

    return render(request, 'marketplace/sell_form.html', {'categories': categories})


@require_http_methods(['GET', 'POST'])
def sell_edit_view(request, sell_id):
    if not request.session.get('user_id'):
        return redirect('login')
    sell = get_object_or_404(SellBook, sell_id=sell_id, user_id=request.session['user_id'])
    categories = Category.objects.all()
    if request.method == 'POST':
        sell.second_price = Decimal(request.POST['second_price'])
        sell.quality = int(request.POST.get('quality', sell.quality))
        sell.book.book_desc = request.POST.get('book_desc', sell.book.book_desc)
        sell.book.save()
        if request.POST.get('status') in ('0', '1'):
            sell.status = int(request.POST['status'])
        sell.save()
        messages.success(request, 'Updated')
        return redirect('book_detail', sell_id=sell.sell_id)
    return render(request, 'marketplace/sell_edit.html', {'sell': sell, 'categories': categories})


def collect_toggle_view(request, sell_id):
    if not request.session.get('user_id'):
        return redirect('login')
    user = getattr(request, 'custom_user', None)
    if not user:
        return redirect('login')
    sell = get_object_or_404(SellBook, sell_id=sell_id)
    obj = Collect.objects.filter(user=user, sell=sell).first()
    if obj:
        obj.delete()
        sell.collect_count = max(0, sell.collect_count - 1)
        messages.info(request, 'Removed from favorites')
    else:
        Collect.objects.create(user=user, sell=sell)
        sell.collect_count += 1
        BehaviorLog.objects.create(user=user, sell=sell, action_type=BehaviorLog.ACTION_COLLECT)
        messages.success(request, 'Added to favorites')
    sell.save(update_fields=['collect_count'])
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('book_detail', sell_id=sell_id)


def collect_batch_remove(request):
    if not request.session.get('user_id'):
        return redirect('login')
    ids = request.POST.getlist('collect_ids')
    Collect.objects.filter(user_id=request.session['user_id'], collect_id__in=ids).delete()
    messages.success(request, 'Batch removed')
    return redirect(reverse('profile') + '?tab=collects')
