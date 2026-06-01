from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, ProfileForm, RegisterForm
from accounts.models import User
from marketplace.models import BrowseHistory, Collect, SellBook
from trade.models import Message, OrderInfo


def _login_user(request, user, remember=False):
    request.session['user_id'] = user.user_id
    request.session['username'] = user.username
    request.session['role'] = user.role
    request.custom_user = user
    if remember:
        request.session.set_expiry(60 * 60 * 24 * 14)
    else:
        request.session.set_expiry(0)


def _logout_user(request):
    request.session.flush()


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.session.get('user_id'):
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if User.objects.filter(username=form.cleaned_data['username']).exists():
            messages.error(request, 'Username already exists')
        elif len(form.cleaned_data['password']) < 6:
            messages.error(request, 'Password min 6 chars')
        else:
            user = User(
                username=form.cleaned_data['username'],
                nickname=form.cleaned_data.get('nickname') or form.cleaned_data['username'],
            )
            user.set_password(form.cleaned_data['password'])
            user.save()
            _login_user(request, user)
            messages.success(request, 'Registered')
            return redirect('home')
    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.session.get('user_id'):
        return redirect('home')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(username=form.cleaned_data['username']).first()
        if not user or not user.check_password(form.cleaned_data['password']):
            messages.error(request, 'Invalid credentials')
        elif not user.is_active:
            messages.error(request, 'Account disabled')
        else:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            _login_user(request, user, remember=bool(request.POST.get('remember')))
            messages.success(request, 'Logged in')
            return redirect(request.GET.get('next', '/'))
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    _logout_user(request)
    messages.info(request, 'Logged out')
    return redirect('home')


@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        user = User.objects.filter(username=username).first()
        if user:
            messages.info(request, 'Contact admin to reset password for: ' + username)
        else:
            messages.error(request, 'User not found')
    return render(request, 'accounts/forgot_password.html')


@require_http_methods(['GET', 'POST'])
def profile_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    user = User.objects.get(user_id=user_id)
    tab = request.GET.get('tab', 'profile')
    form = ProfileForm(request.POST or None, initial={'nickname': user.nickname})

    if request.method == 'POST' and request.POST.get('form_type') == 'profile' and form.is_valid():
        user.nickname = form.cleaned_data['nickname']
        if form.cleaned_data.get('new_password'):
            if not form.cleaned_data.get('old_password') or not user.check_password(form.cleaned_data['old_password']):
                messages.error(request, 'Wrong old password')
            else:
                user.set_password(form.cleaned_data['new_password'])
        user.save()
        messages.success(request, 'Profile updated')
        return redirect('profile')

    order_status = request.GET.get('status')
    orders_buy = OrderInfo.objects.filter(buyer_id=user_id).select_related('sell', 'sell__book', 'seller')
    if order_status is not None and order_status != '':
        orders_buy = orders_buy.filter(order_status=int(order_status))

    ctx = {
        'user': user,
        'form': form,
        'tab': tab,
        'my_sells': SellBook.objects.filter(user_id=user_id).select_related('book', 'book__category'),
        'my_collects': Collect.objects.filter(user_id=user_id).select_related('sell', 'sell__book'),
        'my_orders_buy': orders_buy[:50],
        'my_orders_sell': OrderInfo.objects.filter(seller_id=user_id).select_related('sell', 'sell__book', 'buyer')[:50],
        'browse_history': BrowseHistory.objects.filter(user_id=user_id).select_related('sell', 'sell__book')[:30],
        'unread_messages': Message.objects.filter(receiver_id=user_id, is_read=False).count(),
        'order_status': order_status,
    }
    return render(request, 'accounts/profile.html', ctx)
