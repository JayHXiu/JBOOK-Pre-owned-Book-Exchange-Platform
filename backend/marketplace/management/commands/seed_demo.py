# -*- coding: utf-8 -*-
"""导入 Book-Crossing 数据集到 JBOOK（替代原手工样本库）"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from accounts.models import User
from analytics.models import BehaviorLog, CrawlerLog, DailyReport
from catalog.models import BookBase, Category
from marketplace.data.book_crossing import BookCrossingImporter
from marketplace.models import BrowseHistory, Collect, SellBook
from trade.models import Message, OrderInfo


class Command(BaseCommand):
    help = '从 Book-Crossing 数据集导入图书、用户、评分与行为数据'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='清空业务数据后重新导入')
        parser.add_argument('--max-books', type=int, default=1800, help='导入图书上限（按评分数排序）')
        parser.add_argument('--max-users', type=int, default=280, help='BX 映射用户上限')
        parser.add_argument('--max-ratings', type=int, default=12000, help='导入评分子集上限')

    def handle(self, *args, **options):
        force = options['force']
        if BookBase.objects.exists() and not force:
            self.stdout.write(self.style.WARNING(
                f'已有 {BookBase.objects.count()} 本图书。使用 --force 清空并重新导入 Book-Crossing。'
            ))
            return

        if force:
            self._clear_data()

        self.stdout.write('数据源: Book-Crossing (Ziegler et al., WWW 2005)')
        importer = BookCrossingImporter(
            max_books=options['max_books'],
            max_users=options['max_users'],
            max_ratings=options['max_ratings'],
            stdout=self.stdout.write,
        )
        with transaction.atomic():
            stats = importer.run()
            self._mark_anomalies()

        self.stdout.write(self.style.SUCCESS(
            f'导入完成 — 图书 {stats.books} · 在售 {SellBook.objects.filter(status=SellBook.STATUS_ON).count()} · '
            f'用户 {User.objects.count()} · 评分行为 {stats.ratings_used} · '
            f'行为日志 {stats.behaviors} · 订单 {OrderInfo.objects.count()}'
        ))
        self.stdout.write('演示账号: admin/admin123  seller1/123456  buyer1/123456  bx_*/123456')

    def _clear_data(self):
        self.stdout.write('清空现有业务数据…')
        Message.objects.all().delete()
        OrderInfo.objects.all().delete()
        BrowseHistory.objects.all().delete()
        Collect.objects.all().delete()
        BehaviorLog.objects.all().delete()
        SellBook.objects.all().delete()
        BookBase.objects.all().delete()
        Category.objects.all().delete()
        DailyReport.objects.all().delete()
        CrawlerLog.objects.all().delete()
        User.objects.all().delete()

    def _mark_anomalies(self):
        avg = SellBook.objects.filter(status=SellBook.STATUS_ON).aggregate(a=Avg('second_price'))['a'] or 50
        threshold = float(avg) * 2.5
        stale = timezone.now() - timedelta(days=20)
        for sell in SellBook.objects.filter(status=SellBook.STATUS_ON):
            if float(sell.second_price) > threshold or (sell.view_count == 0 and sell.create_time < stale):
                sell.is_anomaly = True
                sell.save(update_fields=['is_anomaly'])
