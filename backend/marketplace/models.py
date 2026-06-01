from django.db import models

from accounts.models import User
from catalog.models import BookBase


class SellBook(models.Model):
    """在售图书表 sell_book"""

    STATUS_OFF = 0
    STATUS_ON = 1
    STATUS_CHOICES = (
        (STATUS_OFF, '下架'),
        (STATUS_ON, '在售'),
    )

    sell_id = models.AutoField(primary_key=True, db_column='sell_id')
    book = models.ForeignKey(BookBase, on_delete=models.CASCADE, db_column='book_id', related_name='sell_items')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='sell_books')
    second_price = models.DecimalField(max_digits=10, decimal_places=2)
    quality = models.SmallIntegerField(default=3, help_text='成色1-5级')
    cover_img = models.CharField(max_length=512, blank=True, default='')
    view_count = models.IntegerField(default=0)
    collect_count = models.IntegerField(default=0)
    consult_count = models.IntegerField(default=0)
    create_time = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=STATUS_ON, db_index=True)
    is_hot = models.BooleanField(default=False, help_text='热度模型标记')
    is_anomaly = models.BooleanField(default=False, help_text='异常高价/滞销标记')
    audit_status = models.SmallIntegerField(default=1, help_text='0待审1通过2拒绝')

    class Meta:
        db_table = 'sell_book'
        verbose_name = '在售图书'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['book_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
        ]

    @property
    def discount_rate(self):
        if self.book.original_price and float(self.book.original_price) > 0:
            return round(float(self.second_price) / float(self.book.original_price), 2)
        return 0.0


class Collect(models.Model):
    """收藏表 collect"""

    collect_id = models.AutoField(primary_key=True, db_column='collect_id')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='collects')
    sell = models.ForeignKey(SellBook, on_delete=models.CASCADE, db_column='sell_id', related_name='collects')
    collect_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collect'
        verbose_name = '收藏'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'sell')
        indexes = [
            models.Index(fields=['user_id', 'sell_id']),
        ]


class BrowseHistory(models.Model):
    """用户浏览记录"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='browse_history')
    sell = models.ForeignKey(SellBook, on_delete=models.CASCADE, related_name='browsed_by')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'browse_history'
        ordering = ['-viewed_at']
        unique_together = ('user', 'sell')
