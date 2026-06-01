import json
import subprocess
import sys
from pathlib import Path

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from analytics.models import CrawlerLog
from analytics.services import dashboard_payload, ml_dashboard_payload
from catalog.models import BookBase, Category
from marketplace.models import SellBook


def _require_admin(request):
    uid = request.session.get('user_id')
    if not uid:
        return None, redirect('login')
    user = User.objects.filter(user_id=uid).first()
    if not user or not user.is_admin:
        messages.error(request, 'Admin only')
        return None, redirect('home')
    return user, None


def dashboard_public_view(request):
    days = request.GET.get('days', 30)
    cat_id = request.GET.get('cat_id') or None
    data = dashboard_payload(admin=False, days=days, cat_id=cat_id)
    categories = Category.objects.all()
    return render(request, 'analytics/dashboard_public.html', {
        'chart_data': json.dumps(data, ensure_ascii=False),
        'overview': data['overview'],
        'categories': categories,
        'days': days,
        'cat_id': cat_id or '',
    })


def dashboard_admin_view(request):
    user, redir = _require_admin(request)
    if redir:
        return redir
    days = request.GET.get('days', 30)
    cat_id = request.GET.get('cat_id') or None
    data = dashboard_payload(admin=True, days=days, cat_id=cat_id)
    return render(request, 'analytics/dashboard_admin.html', {
        'chart_data': json.dumps(data, ensure_ascii=False),
        'overview': data['overview'],
        'anomaly_high': SellBook.objects.filter(is_anomaly=True, status=SellBook.STATUS_ON).select_related('book', 'user')[:15],
        'anomaly_zero': SellBook.objects.filter(view_count=0, status=SellBook.STATUS_ON).select_related('book')[:15],
        'pending_audit': SellBook.objects.filter(audit_status=0).select_related('book', 'user')[:20],
        'users': User.objects.all().order_by('-register_time')[:50],
        'categories': Category.objects.all(),
        'crawler_logs': CrawlerLog.objects.all()[:10],
        'days': days,
        'cat_id': cat_id or '',
    })


def ml_dashboard_view(request):
    is_admin = request.session.get('role') == 1
    default_view = 'standard' if request.session.get('user_id') else 'lite'
    view_mode = request.GET.get('view', default_view)
    if view_mode == 'pro' and not is_admin:
        view_mode = 'standard'
    if view_mode not in ('lite', 'standard', 'pro'):
        view_mode = default_view
    from mlapp.analysis import build_model_analysis_payload
    data = build_model_analysis_payload(view_mode, is_admin)
    return render(request, 'analytics/ml_dashboard.html', {
        'ml_data': json.dumps(data, ensure_ascii=False),
        'view_mode': view_mode,
        'is_admin': is_admin,
    })


def api_ml_analysis(request):
    is_admin = request.session.get('role') == 1
    view_mode = request.GET.get('view', 'standard')
    if view_mode == 'pro' and not is_admin:
        return JsonResponse({'error': 'forbidden'}, status=403)
    from mlapp.analysis import build_model_analysis_payload
    return JsonResponse(build_model_analysis_payload(view_mode, is_admin))


def api_dashboard_data(request):
    admin = request.GET.get('admin') == '1'
    if admin:
        _, redir = _require_admin(request)
        if redir:
            return JsonResponse({'error': 'forbidden'}, status=403)
    days = request.GET.get('days', 30)
    cat_id = request.GET.get('cat_id') or None
    return JsonResponse(dashboard_payload(admin=admin, days=days, cat_id=cat_id))


def audit_sell_view(request, sell_id):
    user, redir = _require_admin(request)
    if redir:
        return redir
    sell = SellBook.objects.get(sell_id=sell_id)
    action = request.POST.get('action')
    if action == 'pass':
        sell.audit_status = 1
    elif action == 'reject':
        sell.audit_status = 2
        sell.status = SellBook.STATUS_OFF
    sell.save()
    messages.success(request, 'Audit done')
    return redirect('dashboard_admin')


@require_POST
def toggle_user_active(request, user_id):
    user, redir = _require_admin(request)
    if redir:
        return redir
    target = get_object_or_404(User, user_id=user_id)
    if target.is_admin:
        messages.error(request, 'Cannot disable admin')
        return redirect('admin_manage')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    return redirect('admin_manage')


@require_http_methods(['GET', 'POST'])
def admin_manage_view(request):
    user, redir = _require_admin(request)
    if redir:
        return redir

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_category':
            name = request.POST.get('cat_name', '').strip()
            if name:
                Category.objects.create(cat_name=name)
                messages.success(request, 'Category added')
        elif action == 'delete_category':
            cid = request.POST.get('cat_id')
            Category.objects.filter(cat_id=cid).delete()
            messages.info(request, 'Category deleted')

    return render(request, 'analytics/admin_manage.html', {
        'users': User.objects.all().order_by('-register_time'),
        'categories': Category.objects.all(),
        'pending_audit': SellBook.objects.filter(audit_status=0).select_related('book', 'user'),
        'crawler_logs': CrawlerLog.objects.all()[:15],
    })


@require_POST
def trigger_crawler_view(request):
    """同步 Book-Crossing 原始 CSV（管理员数据管理页触发）"""
    user, redir = _require_admin(request)
    if redir:
        return redir
    log = CrawlerLog.objects.create(status=CrawlerLog.STATUS_RUNNING, message='Book-Crossing download started')
    root = Path(__file__).resolve().parents[2].parent
    script = root / 'data' / 'book_crossing' / 'download.py'
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=600,
        )
        log.status = CrawlerLog.STATUS_OK if result.returncode == 0 else CrawlerLog.STATUS_FAIL
        log.message = (result.stdout or result.stderr or '')[-800:]
        log.records_count = BookBase.objects.count()
        log.finished_at = timezone.now()
        log.save()
        if result.returncode == 0:
            messages.success(request, 'Book-Crossing CSV sync finished')
        else:
            messages.error(request, 'Download failed — see crawler log')
    except Exception as e:
        log.status = CrawlerLog.STATUS_FAIL
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        messages.error(request, 'Download failed')
    return redirect('admin_manage')
