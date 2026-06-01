from django.contrib import admin

from trade.models import Message, OrderInfo


@admin.register(OrderInfo)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'buyer', 'seller', 'deal_price', 'order_status', 'create_time')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('msg_id', 'sender', 'receiver', 'is_read', 'create_time')
