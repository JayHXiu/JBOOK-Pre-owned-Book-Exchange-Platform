from django.urls import path

from marketplace import api_views, views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('books/', views.book_list_view, name='book_list'),
    path('books/<int:sell_id>/', views.book_detail_view, name='book_detail'),
    path('sell/new/', views.sell_create_view, name='sell_create'),
    path('sell/<int:sell_id>/edit/', views.sell_edit_view, name='sell_edit'),
    path('collect/<int:sell_id>/', views.collect_toggle_view, name='collect_toggle'),
    path('collect/batch-remove/', views.collect_batch_remove, name='collect_batch_remove'),
    path('api/suggest-price/', api_views.api_suggest_price, name='api_suggest_price'),
    path('api/isbn/', api_views.api_isbn_lookup, name='api_isbn'),
    path('api/search-suggest/', api_views.api_search_suggest, name='api_search_suggest'),
]
