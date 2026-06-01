import uuid

from django.db import models

from accounts.models import User
from marketplace.models import SellBook


class OrderInfo(models.Model):
    """订单表 order_info"""

    STATUS_PENDING = 0
    STATUS_COMMUNICATING = 1
    STATUS_TRADING = 2
    STATUS_DONE = 3
    STATUS_CHOICES = (
        (STATUS_PENDING, '待沟通'),
        (STATUS_COMMUNICATING, '沟通中'),
        (STATUS_TRADING, '待交易'),
        (STATUS_DONE, '已完成'),
    )

    order_id = models.CharField(max_length=32, primary_key=True, default='')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, db_column='buyer_id', related_name='buy_orders')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, db_column='seller_id', related_name='sell_orders')
    sell = models.ForeignKey(SellBook, on_delete=models.PROTECT, db_column='sell_id', related_name='orders')
    deal_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_status = models.SmallIntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    create_time = models.DateTimeField(auto_now_add=True)
    finish_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'order_info'
        verbose_name = '订单'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['buyer_id']),
            models.Index(fields=['seller_id']),
            models.Index(fields=['sell_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = uuid.uuid4().hex[:16].upper()
        super().save(*args, **kwargs)


class Message(models.Model):
    """私信咨询"""

    msg_id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    sell = models.ForeignKey(SellBook, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message'
        ordering = ['-create_time']
