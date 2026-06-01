"""图书列表筛选、首页数据聚合"""
from django.db.models import Avg, Min, Max, Q
from django.utils import timezone

from catalog.models import BookBase, Category
from marketplace.models import BrowseHistory, Collect, SellBook


SORT_MAP = {
    '-create_time': '-create_time',
    'create_time': 'create_time',
    'price': 'second_price',
    '-price': '-second_price',
    'view_count': 'view_count',
    '-view_count': '-view_count',
    'hot': '-view_count',
}


def filter_sell_queryset(request):
    qs = SellBook.objects.filter(status=SellBook.STATUS_ON, audit_status=1).select_related(
        'book', 'book__category', 'user'
    )
    keyword = request.GET.get('q', '').strip()
    cat_id = request.GET.get('cat_id')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    qualities = request.GET.getlist('quality')

    if keyword:
        qs = qs.filter(
            Q(book__book_name__icontains=keyword)
            | Q(book__author__icontains=keyword)
            | Q(book__isbn__icontains=keyword)
        )
    if cat_id:
        qs = qs.filter(book__category_id=cat_id)
    if min_price not in (None, ''):
        qs = qs.filter(second_price__gte=min_price)
    if max_price not in (None, ''):
        qs = qs.filter(second_price__lte=max_price)
    if qualities:
        qs = qs.filter(quality__in=qualities)

    sort = request.GET.get('sort', '-create_time')
    qs = qs.order_by(SORT_MAP.get(sort, '-create_time'))
    return qs, keyword


def price_bounds():
    agg = SellBook.objects.filter(status=SellBook.STATUS_ON, audit_status=1).aggregate(
        mn=Min('second_price'), mx=Max('second_price')
    )
    return float(agg['mn'] or 0), float(agg['mx'] or 200)


def home_sections():
    base = SellBook.objects.filter(status=SellBook.STATUS_ON, audit_status=1).select_related(
        'book', 'book__category', 'user'
    )
    hot = base.order_by('-is_hot', '-view_count')[:8]
    latest = base.order_by('-create_time')[:8]
    low_price = base.order_by('second_price')[:8]
    categories = Category.objects.filter(parent__isnull=True)[:8]
    return {
        'hot_books': hot,
        'latest_books': latest,
        'low_price_books': low_price,
        'root_categories': categories,
    }


def record_browse(user_id, sell):
    if not user_id:
        return
    BrowseHistory.objects.update_or_create(
        user_id=user_id, sell=sell,
        defaults={'viewed_at': timezone.now()},
    )


def isbn_lookup(isbn):
    book = BookBase.objects.filter(isbn=isbn).select_related('category').first()
    if not book:
        return None
    return {
        'isbn': book.isbn,
        'book_name': book.book_name,
        'author': book.author,
        'publisher': book.publisher,
        'pub_year': book.pub_year,
        'original_price': float(book.original_price),
        'cat_id': book.category_id,
        'cat_name': book.category.cat_name,
        'book_desc': book.book_desc,
    }


def search_suggestions(q, limit=8):
    if not q or len(q) < 1:
        return []
    books = BookBase.objects.filter(
        Q(book_name__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q)
    ).values('book_name', 'author', 'isbn')[:limit]
    return list(books)
