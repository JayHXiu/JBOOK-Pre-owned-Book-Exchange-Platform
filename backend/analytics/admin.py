from django.contrib import admin

from analytics.models import BehaviorLog, DailyReport


@admin.register(BehaviorLog)
class BehaviorLogAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'user', 'sell', 'action_type', 'action_time')


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'new_users', 'new_sells', 'orders_done', 'total_views')
