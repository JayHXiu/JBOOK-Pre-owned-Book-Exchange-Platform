from django.contrib import admin

from catalog.models import BookBase, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('cat_id', 'cat_name', 'parent')


@admin.register(BookBase)
class BookBaseAdmin(admin.ModelAdmin):
    list_display = ('book_id', 'book_name', 'isbn', 'author', 'original_price', 'category')
    search_fields = ('book_name', 'isbn', 'author')
    list_filter = ('category',)
