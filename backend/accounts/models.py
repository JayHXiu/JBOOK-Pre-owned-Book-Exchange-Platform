from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class User(models.Model):
    """用户表 user"""

    ROLE_USER = 0
    ROLE_ADMIN = 1
    ROLE_CHOICES = (
        (ROLE_USER, '普通用户'),
        (ROLE_ADMIN, '管理员'),
    )

    user_id = models.AutoField(primary_key=True, db_column='user_id')
    username = models.CharField(max_length=64, unique=True, db_index=True)
    password = models.CharField(max_length=128)
    nickname = models.CharField(max_length=64, blank=True, default='')
    role = models.SmallIntegerField(choices=ROLE_CHOICES, default=ROLE_USER)
    register_time = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    avatar = models.CharField(max_length=512, blank=True, default='')

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.nickname or self.username

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def pk(self):
        return self.user_id
