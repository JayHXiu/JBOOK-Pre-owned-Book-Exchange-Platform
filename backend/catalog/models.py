from django.db import models


class Category(models.Model):
    """图书类目表 category"""

    cat_id = models.AutoField(primary_key=True, db_column='cat_id')
    cat_name = models.CharField(max_length=64)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        db_column='parent_id', related_name='children',
    )

    class Meta:
        db_table = 'category'
        verbose_name = '图书类目'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.cat_name


class BookBase(models.Model):
    """图书基础信息表 book_base（爬虫同步静态数据）"""

    book_id = models.AutoField(primary_key=True, db_column='book_id')
    isbn = models.CharField(max_length=20, unique=True, db_index=True)
    book_name = models.CharField(max_length=200, db_index=True)
    author = models.CharField(max_length=128, blank=True, default='')
    publisher = models.CharField(max_length=128, blank=True, default='')
    pub_year = models.IntegerField(null=True, blank=True)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, db_column='cat_id', related_name='books',
    )
    book_desc = models.TextField(blank=True, default='')
    tags = models.CharField(max_length=256, blank=True, default='', help_text='逗号分隔标签')

    class Meta:
        db_table = 'book_base'
        verbose_name = '图书基础信息'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.book_name
