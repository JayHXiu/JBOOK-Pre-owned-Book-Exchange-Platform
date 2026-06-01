from django.contrib import admin

from marketplace.models import Collect, SellBook


@admin.register(SellBook)
class SellBookAdmin(admin.ModelAdmin):
    list_display = ('sell_id', 'book', 'user', 'second_price', 'status', 'view_count', 'is_hot', 'is_anomaly')


@admin.register(Collect)
class CollectAdmin(admin.ModelAdmin):
    list_display = ('collect_id', 'user', 'sell', 'collect_time')
