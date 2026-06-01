from django.urls import path

from analytics import views

urlpatterns = [
    path('dashboard/', views.dashboard_public_view, name='dashboard_public'),
    path('admin/', views.dashboard_admin_view, name='dashboard_admin'),
    path('ml/', views.ml_dashboard_view, name='ml_dashboard'),
    path('manage/', views.admin_manage_view, name='admin_manage'),
    path('api/data/', views.api_dashboard_data, name='api_dashboard'),
    path('api/ml/', views.api_ml_analysis, name='api_ml_analysis'),
    path('admin/audit/<int:sell_id>/', views.audit_sell_view, name='audit_sell'),
    path('admin/user/<int:user_id>/toggle/', views.toggle_user_active, name='toggle_user'),
    path('admin/crawler/', views.trigger_crawler_view, name='trigger_crawler'),
]
