# -*- coding: utf-8 -*-
"""
一键初始化 JBOOK 业务数据（首页/书市可见）。

数据源（--source auto 时自动选择）：
  1. PostgreSQL 表 book/users/ratings（load_bx.py 已导入时）
  2. 本地 CSV + BookCrossingImporter（seed_demo 同等逻辑）
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from accounts.models import User
from analytics.models import BehaviorLog, CrawlerLog, DailyReport
from catalog.models import BookBase, Category
from marketplace.data.book_crossing import BookCrossingImporter
from marketplace.data.pg_sync import PgBookCrossingImporter, bx_pg_tables_ready
from marketplace.models import BrowseHistory, Collect, SellBook
from trade.models import Message, OrderInfo


class Command(BaseCommand):
    help = '初始化 JBOOK：迁移业务表 + 从 PG BX 表或 CSV 导入在售图书'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            choices=('auto', 'pg', 'csv'),
            default='auto',
            help='auto=有 PG BX 表则用 pg，否则 csv',
        )
        parser.add_argument('--force', action='store_true', help='清空业务表后重新导入')
        parser.add_argument('--max-books', type=int, default=1800)
        parser.add_argument('--max-users', type=int, default=280)
        parser.add_argument('--max-ratings', type=int, default=12000)

    def handle(self, *args, **options):
        force = options['force']
        on_sale = SellBook.objects.filter(
            status=SellBook.STATUS_ON, audit_status=1,
        ).count()

        if on_sale > 0 and not force:
            self.stdout.write(self.style.SUCCESS(
                f'已有 {on_sale} 条在售图书，跳过导入。使用 --force 重新初始化。'
            ))
            return

        if force:
            self._clear_data()

        source = options['source']
        if source == 'auto':
            source = 'pg' if bx_pg_tables_ready() else 'csv'

        self.stdout.write(f'数据源: {source}')

        common = dict(
            max_books=options['max_books'],
            max_users=options['max_users'],
            max_ratings=options['max_ratings'],
            stdout=self.stdout.write,
        )

        if source == 'pg':
            if not bx_pg_tables_ready():
                self.stderr.write(
                    '未找到 PostgreSQL 表 book 或表为空。请先运行 load_bx.py 或使用 --source csv'
                )
                return
            importer = PgBookCrossingImporter(**common)
        else:
            importer = BookCrossingImporter(**common)

        with transaction.atomic():
            stats = importer.run()
            # 确保首页展示（原逻辑前 3 条 audit_status=0）
            SellBook.objects.filter(status=SellBook.STATUS_ON).update(audit_status=1)
            self._mark_anomalies()

        on_sale = SellBook.objects.filter(
            status=SellBook.STATUS_ON, audit_status=1,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f'完成 — 图书 {stats.books} · 在售(已审核) {on_sale} · '
            f'用户 {User.objects.count()} · 行为 {stats.behaviors}'
        ))
        self.stdout.write('演示账号: admin/admin123  seller1/123456  buyer1/123456')

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
        avg = SellBook.objects.filter(status=SellBook.STATUS_ON).aggregate(
            a=Avg('second_price'),
        )['a'] or 50
        threshold = float(avg) * 2.5
        stale = timezone.now() - timedelta(days=20)
        for sell in SellBook.objects.filter(status=SellBook.STATUS_ON):
            if float(sell.second_price) > threshold or (
                sell.view_count == 0 and sell.create_time < stale
            ):
                sell.is_anomaly = True
                sell.save(update_fields=['is_anomaly'])
