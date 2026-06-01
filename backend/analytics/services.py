"""数据分析服务 - ECharts 看板聚合（支持筛选联动）"""
from datetime import datetime, timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from django.utils import timezone

from accounts.models import User
from analytics.models import BehaviorLog
from catalog.models import BookBase, Category
from marketplace.models import SellBook
from trade.models import OrderInfo


def _parse_days(request_days, default=30):
    try:
        d = int(request_days)
        return max(7, min(d, 90))
    except (TypeError, ValueError):
        return default


def _sell_qs(cat_id=None):
    qs = SellBook.objects.filter(status=SellBook.STATUS_ON, audit_status=1)
    if cat_id:
        qs = qs.filter(book__category_id=cat_id)
    return qs


def overview_metrics(cat_id=None):
    today = timezone.now().date()
    sell_qs = _sell_qs(cat_id)
    total_books = sell_qs.count()
    total_users = User.objects.filter(is_active=True).count()
    orders_done = OrderInfo.objects.filter(order_status=OrderInfo.STATUS_DONE).count()
    views_today = BehaviorLog.objects.filter(
        action_type=BehaviorLog.ACTION_VIEW, action_time__date=today,
    ).count()
    top_cats = list(
        SellBook.objects.filter(status=SellBook.STATUS_ON, audit_status=1)
        .values('book__category__cat_name')
        .annotate(cnt=Count('sell_id'))
        .order_by('-cnt')[:5]
    )
    return {
        'total_users': total_users,
        'total_books': BookBase.objects.count(),
        'on_sale': total_books,
        'orders_done': orders_done,
        'views_today': views_today,
        'top_cats': top_cats,
    }


def category_stock_pie(cat_id=None):
    rows = (
        _sell_qs(cat_id)
        .values('book__category__cat_name')
        .annotate(value=Count('sell_id'))
        .order_by('-value')
    )
    return [
        {'name': r['book__category__cat_name'] or 'Other', 'value': r['value']}
        for r in rows
    ]


def category_bar_counts(cat_id=None):
    rows = (
        _sell_qs(cat_id)
        .values('book__category__cat_name')
        .annotate(value=Count('sell_id'))
        .order_by('-value')
    )
    return {
        'categories': [r['book__category__cat_name'] or 'Other' for r in rows],
        'counts': [r['value'] for r in rows],
    }


def category_monthly_orders(days=180, cat_id=None):
    since = timezone.now() - timedelta(days=days)
    qs = OrderInfo.objects.filter(create_time__gte=since)
    if cat_id:
        qs = qs.filter(sell__book__category_id=cat_id)
    rows = qs.annotate(month=TruncMonth('create_time')).values(
        'sell__book__category__cat_name', 'month'
    ).annotate(cnt=Count('order_id'))
    cats = sorted({r['sell__book__category__cat_name'] or 'Other' for r in rows})
    months = sorted({r['month'].strftime('%Y-%m') for r in rows if r['month']})
    series = []
    for cat in cats:
        data = []
        for m in months:
            cnt = sum(
                r['cnt'] for r in rows
                if (r['sell__book__category__cat_name'] or 'Other') == cat
                and r['month'] and r['month'].strftime('%Y-%m') == m
            )
            data.append(cnt)
        series.append({'name': cat, 'data': data})
    return {'months': months, 'series': series}


def price_histogram(cat_id=None):
    prices = list(_sell_qs(cat_id).values_list('second_price', flat=True))
    bins = [0, 20, 40, 60, 80, 100, 150, 200, 500]
    labels, counts = [], []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        labels.append(f'{lo}-{hi}')
        counts.append(sum(1 for p in prices if lo <= float(p) < hi))
    return {'labels': labels, 'counts': counts}


def price_gap_by_category(cat_id=None):
    rows = (
        _sell_qs(cat_id)
        .values('book__category__cat_name')
        .annotate(avg_second=Avg('second_price'), avg_original=Avg('book__original_price'))
    )
    cats, gap = [], []
    for r in rows:
        cats.append(r['book__category__cat_name'] or 'Other')
        o = float(r['avg_original'] or 1)
        s = float(r['avg_second'] or 0)
        gap.append(round((o - s) / o * 100, 1) if o else 0)
    return {'categories': cats, 'gap_percent': gap}


def behavior_heatmap(days=7, cat_id=None):
    since = timezone.now() - timedelta(days=days)
    qs = BehaviorLog.objects.filter(action_time__gte=since)
    if cat_id:
        qs = qs.filter(sell__book__category_id=cat_id)
    rows = qs.annotate(hour=TruncHour('action_time')).values('hour').annotate(cnt=Count('log_id'))
    return [[r['hour'].weekday() if r['hour'] else 0, r['hour'].hour if r['hour'] else 0, r['cnt']] for r in rows]


def conversion_funnel(cat_id=None):
    qs = BehaviorLog.objects.all()
    if cat_id:
        qs = qs.filter(sell__book__category_id=cat_id)
    views = qs.filter(action_type=BehaviorLog.ACTION_VIEW).count()
    collects = qs.filter(action_type=BehaviorLog.ACTION_COLLECT).count()
    consults = qs.filter(action_type=BehaviorLog.ACTION_CONSULT).count()
    orders = qs.filter(action_type=BehaviorLog.ACTION_ORDER).count()
    return [
        {'name': 'View', 'value': max(views, 1)},
        {'name': 'Collect', 'value': collects},
        {'name': 'Consult', 'value': consults},
        {'name': 'Order', 'value': orders},
    ]


def trend_series(days=30, cat_id=None):
    since = timezone.now() - timedelta(days=days)
    dates = [(since + timedelta(days=i)).date() for i in range(days + 1)]
    labels = [d.strftime('%m-%d') for d in dates]

    def build(model_qs, date_field):
        dmap = dict(
            model_qs.filter(**{f'{date_field}__date__gte': since.date()})
            .annotate(d=TruncDate(date_field))
            .values('d')
            .annotate(c=Count('pk'))
            .values_list('d', 'c')
        )
        return [dmap.get(d, 0) for d in dates]

    sell_qs = SellBook.objects.all()
    order_qs = OrderInfo.objects.all()
    view_qs = BehaviorLog.objects.filter(action_type=BehaviorLog.ACTION_VIEW)
    if cat_id:
        sell_qs = sell_qs.filter(book__category_id=cat_id)
        order_qs = order_qs.filter(sell__book__category_id=cat_id)
        view_qs = view_qs.filter(sell__book__category_id=cat_id)

    sells = build(sell_qs, 'create_time')
    orders = build(order_qs, 'create_time')
    views = build(view_qs, 'action_time')
    avg_prices = []
    for d in dates:
        avg = sell_qs.filter(create_time__date=d).aggregate(a=Avg('second_price'))['a']
        avg_prices.append(round(float(avg or 0), 2))

    return {
        'labels': labels,
        'sells': sells,
        'orders': orders,
        'views': views,
        'avg_prices': avg_prices,
    }


def anomaly_lists():
    return {
        'high_price': list(
            SellBook.objects.filter(is_anomaly=True, status=SellBook.STATUS_ON)
            .select_related('book', 'user')[:15]
        ),
        'zero_view': list(
            SellBook.objects.filter(view_count=0, status=SellBook.STATUS_ON)
            .select_related('book')[:15]
        ),
        'stale': list(
            SellBook.objects.filter(is_anomaly=True)
            .exclude(view_count=0)
            .select_related('book')[:10]
        ),
    }


def dashboard_payload(admin=False, days=30, cat_id=None):
    days = int(days)
    cid = int(cat_id) if cat_id else None
    payload = {
        'overview': overview_metrics(cid),
        'category_pie': category_stock_pie(cid),
        'category_bar': category_bar_counts(cid),
        'category_orders_stack': category_monthly_orders(days, cid),
        'price_hist': price_histogram(cid),
        'price_gap': price_gap_by_category(cid),
        'funnel': conversion_funnel(cid),
        'trend': trend_series(days, cid),
        'days': days,
        'cat_id': cid,
    }
    if admin:
        payload['heatmap'] = behavior_heatmap(min(days, 14), cid)
    return payload


def ml_dashboard_payload(view_mode='standard', is_admin=False):
    """兼容旧调用，转发至模型分析模块"""
    from mlapp.analysis import build_model_analysis_payload
    return build_model_analysis_payload(view_mode, is_admin)
