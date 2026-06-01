from django.db import models

from accounts.models import User
from marketplace.models import SellBook


class BehaviorLog(models.Model):
    """用户行为日志表 behavior_log"""

    ACTION_VIEW = 1
    ACTION_CONSULT = 2
    ACTION_CLICK = 3
    ACTION_COLLECT = 4
    ACTION_ORDER = 5
    ACTION_CHOICES = (
        (ACTION_VIEW, '浏览'),
        (ACTION_CONSULT, '咨询'),
        (ACTION_CLICK, '点击'),
        (ACTION_COLLECT, '收藏'),
        (ACTION_ORDER, '下单'),
    )

    log_id = models.AutoField(primary_key=True, db_column='log_id')
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        db_column='user_id', related_name='behavior_logs',
    )
    sell = models.ForeignKey(SellBook, on_delete=models.CASCADE, db_column='sell_id', related_name='behavior_logs')
    action_type = models.SmallIntegerField(choices=ACTION_CHOICES)
    stay_time = models.IntegerField(default=0, help_text='停留秒数')
    action_time = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'behavior_log'
        verbose_name = '行为日志'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['sell_id']),
            models.Index(fields=['action_time']),
        ]


class DailyReport(models.Model):
    """每日报表"""

    report_date = models.DateField(unique=True)
    new_users = models.IntegerField(default=0)
    new_sells = models.IntegerField(default=0)
    orders_done = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    report_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'daily_report'
        ordering = ['-report_date']


class CrawlerLog(models.Model):
    """爬虫执行日志"""

    STATUS_OK = 'ok'
    STATUS_FAIL = 'fail'
    STATUS_RUNNING = 'running'

    log_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=16, default=STATUS_RUNNING)
    message = models.TextField(blank=True, default='')
    records_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'crawler_log'
        ordering = ['-started_at']
