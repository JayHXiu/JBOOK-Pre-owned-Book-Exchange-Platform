from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'nickname', 'role', 'register_time', 'last_login')
    search_fields = ('username', 'nickname')
    list_filter = ('role',)
