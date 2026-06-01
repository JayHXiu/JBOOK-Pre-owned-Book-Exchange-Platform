from django.urls import path

from trade import views

urlpatterns = [
    path('order/create/<int:sell_id>/', views.create_order_view, name='order_create'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<str:order_id>/status/', views.order_update_status_view, name='order_update_status'),
    path('messages/', views.message_list_view, name='messages'),
    path('messages/poll/', views.api_messages_poll, name='messages_poll'),
    path('messages/<int:sell_id>/', views.message_send_view, name='message_send'),
]
