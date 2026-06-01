"""JBOOK 每日运营报表与异常监控"""
import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from accounts.models import User
from analytics.models import BehaviorLog, DailyReport
from analytics.services import overview_metrics
from marketplace.models import SellBook


class Command(BaseCommand):
    help = '生成前一日运营日报并标记异常图书'

    def handle(self, *args, **options):
        yesterday = timezone.now().date() - timedelta(days=1)
        metrics = overview_metrics()

        new_users = User.objects.filter(register_time__date=yesterday).count()
        new_sells = SellBook.objects.filter(create_time__date=yesterday).count()
        views = BehaviorLog.objects.filter(action_time__date=yesterday, action_type=BehaviorLog.ACTION_VIEW).count()

        report, _ = DailyReport.objects.update_or_create(
            report_date=yesterday,
            defaults={
                'new_users': new_users,
                'new_sells': new_sells,
                'orders_done': metrics['orders_done'],
                'total_views': views,
                'report_json': metrics,
            },
        )

        avg_price = SellBook.objects.filter(status=SellBook.STATUS_ON).aggregate(a=Avg('second_price'))['a'] or 50
        threshold = float(avg_price) * 3
        SellBook.objects.filter(status=SellBook.STATUS_ON).update(is_anomaly=False)
        for s in SellBook.objects.filter(status=SellBook.STATUS_ON):
            if float(s.second_price) > threshold or (s.view_count == 0 and (timezone.now() - s.create_time).days > 14):
                s.is_anomaly = True
                s.save(update_fields=['is_anomaly'])

        log_path = timezone.now().strftime('%Y%m%d') + '_daily.log'
        self.stdout.write(self.style.SUCCESS(f'日报已生成: {report.report_date}'))
        self.stdout.write(json.dumps(metrics, ensure_ascii=False, indent=2))
