from decimal import Decimal

from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from analytics.models import BehaviorLog
from marketplace.models import SellBook
from trade.models import Message, OrderInfo


@require_http_methods(['GET', 'POST'])
def create_order_view(request, sell_id):
    if not request.session.get('user_id'):
        return redirect('login')
    sell = get_object_or_404(SellBook, sell_id=sell_id, status=SellBook.STATUS_ON)
    buyer_id = request.session['user_id']
    if sell.user_id == buyer_id:
        messages.error(request, 'Cannot buy your own book')
        return redirect('book_detail', sell_id=sell_id)
    if request.method == 'POST':
        order = OrderInfo.objects.create(
            buyer_id=buyer_id, seller_id=sell.user_id, sell=sell,
            deal_price=Decimal(request.POST.get('deal_price', sell.second_price)),
            order_status=OrderInfo.STATUS_PENDING,
        )
        BehaviorLog.objects.create(user_id=buyer_id, sell=sell, action_type=BehaviorLog.ACTION_ORDER)
        messages.success(request, f'Order created: {order.order_id}')
        return redirect('order_list')
    return render(request, 'trade/order_create.html', {'sell': sell})


def order_list_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    uid = request.session['user_id']
    role = request.GET.get('role', 'buy')
    status = request.GET.get('status')
    if role == 'sell':
        orders = OrderInfo.objects.filter(seller_id=uid)
    else:
        orders = OrderInfo.objects.filter(buyer_id=uid)
    if status not in (None, ''):
        orders = orders.filter(order_status=int(status))
    orders = orders.select_related('sell', 'sell__book', 'buyer', 'seller').order_by('-create_time')
    return render(request, 'trade/order_list.html', {
        'orders': orders, 'role': role, 'status': status,
    })


@require_http_methods(['POST'])
def order_update_status_view(request, order_id):
    if not request.session.get('user_id'):
        return redirect('login')
    order = get_object_or_404(OrderInfo, order_id=order_id)
    uid = request.session['user_id']
    if uid not in (order.buyer_id, order.seller_id):
        messages.error(request, 'No permission')
        return redirect('order_list')
    new_status = int(request.POST.get('status', order.order_status))
    order.order_status = new_status
    if new_status == OrderInfo.STATUS_DONE:
        order.finish_time = timezone.now()
    order.save()
    messages.success(request, 'Status updated')
    return redirect('order_list')


def _build_threads(uid):
    threads = []
    seen = set()
    for m in Message.objects.filter(
        models.Q(sender_id=uid) | models.Q(receiver_id=uid)
    ).select_related('sender', 'receiver', 'sell', 'sell__book').order_by('-create_time'):
        other_id = m.receiver_id if m.sender_id == uid else m.sender_id
        key = (other_id, m.sell_id or 0)
        if key in seen:
            continue
        seen.add(key)
        other = m.receiver if m.sender_id == uid else m.sender
        unread = Message.objects.filter(sender_id=other_id, receiver_id=uid, is_read=False).count()
        threads.append({'other': other, 'sell': m.sell, 'last': m, 'unread': unread})
    return threads


@require_http_methods(['GET', 'POST'])
def message_list_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    uid = request.session['user_id']
    partner_id = request.GET.get('with')
    sell_id = request.GET.get('sell_id')

    if request.method == 'POST':
        receiver_id = int(request.POST['receiver_id'])
        content = request.POST.get('content', '').strip()
        sid = request.POST.get('sell_id')
        if content:
            Message.objects.create(
                sender_id=uid, receiver_id=receiver_id,
                sell_id=int(sid) if sid else None, content=content,
            )
            if sid:
                sell = SellBook.objects.get(sell_id=sid)
                sell.consult_count += 1
                sell.save(update_fields=['consult_count'])
                BehaviorLog.objects.create(
                    user_id=uid, sell_id=sid, action_type=BehaviorLog.ACTION_CONSULT,
                )
        return redirect(f"{reverse('messages')}?with={receiver_id}" + (f"&sell_id={sid}" if sid else ''))

    threads = _build_threads(uid)
    chat_messages = []
    active_partner = None
    active_sell = None
    if partner_id:
        active_partner = get_object_or_404(User, user_id=int(partner_id))
        qs = Message.objects.filter(
            models.Q(sender_id=uid, receiver_id=partner_id)
            | models.Q(sender_id=partner_id, receiver_id=uid)
        )
        if sell_id:
            qs = qs.filter(sell_id=int(sell_id))
            active_sell = SellBook.objects.filter(sell_id=sell_id).select_related('book').first()
        chat_messages = list(qs.select_related('sender').order_by('create_time'))
        Message.objects.filter(sender_id=partner_id, receiver_id=uid, is_read=False).update(is_read=True)

    return render(request, 'trade/messages.html', {
        'threads': threads,
        'chat_messages': chat_messages,
        'active_partner': active_partner,
        'active_sell': active_sell,
        'partner_id': partner_id,
        'sell_id': sell_id,
    })


@require_GET
def api_messages_poll(request):
    if not request.session.get('user_id'):
        return JsonResponse({'error': 'login'}, status=401)
    uid = request.session['user_id']
    partner_id = request.GET.get('with')
    if not partner_id:
        unread = Message.objects.filter(receiver_id=uid, is_read=False).count()
        return JsonResponse({'unread': unread})
    msgs = Message.objects.filter(
        models.Q(sender_id=uid, receiver_id=partner_id)
        | models.Q(sender_id=partner_id, receiver_id=uid)
    ).order_by('create_time')
    data = [{
        'id': m.msg_id,
        'from_me': m.sender_id == uid,
        'content': m.content,
        'time': m.create_time.strftime('%H:%M'),
    } for m in msgs]
    return JsonResponse({'messages': data})


def message_send_view(request, sell_id):
    if not request.session.get('user_id'):
        return redirect('login')
    sell = get_object_or_404(SellBook, sell_id=sell_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender_id=request.session['user_id'],
                receiver_id=sell.user_id,
                sell=sell, content=content,
            )
            sell.consult_count += 1
            sell.save(update_fields=['consult_count'])
            BehaviorLog.objects.create(
                user_id=request.session['user_id'],
                sell=sell, action_type=BehaviorLog.ACTION_CONSULT,
            )
            return redirect(f"{reverse('messages')}?with={sell.user_id}&sell_id={sell.sell_id}")
    return render(request, 'trade/message_send.html', {'sell': sell})
